"""Cached, source-aligned candidate regeneration. Never edits source or v1 history."""
import json
import re
from collections import Counter
from io import BytesIO
from statistics import median

from pypdf import PdfReader
from jsonschema import Draft202012Validator

from .segmentation import terminal
from .text import normalize
from .validation import ROOT, digest, load_config, validate_dataset
from .followup import overlay_history
from .reviewed import write_immutable
from .annotations import task, write_rows, read_rows, validate_rows, TASK_VALIDATOR

VERSION = 'orbit-segmentation-2.0.0'
TRANSFER_VALIDATOR = Draft202012Validator(json.loads((ROOT/'schemas/v2/annotation_transfer.schema.json').read_text()))
MARKER = re.compile(r'^(PRESIDENT OBAMA:|PRIME MINISTER YATSENYUK:|THE PRESIDENT:|Q(?=\s))')
ADDRESS = re.compile(r'^(?:Mr\. President|Monsieur le Président|Excellencies|Excellences|Distinguished [^.,]+|Ladies and Gentlemen|Mesdames et Messieurs)[,.]?$', re.I)
ABBREVIATIONS = re.compile(r'(?:\b(?:Mr|Mrs|Ms|Dr|Prof|St|Mme|M|H\.E|U\.S|U\.N|e\.g|i\.e)|\b[A-Z])\.$', re.I)


def layout_header_line(line):
    # Exact layout templates only: a body sentence beginning "UN General Assembly"
    # must never be removed merely because its prefix resembles a header.
    return bool(re.fullmatch(r'(?:\d+|V\d+|-?Courtesy Translation-?|UNOFFICIAL TRANSLATION|CHECK AGAINST DELIVERY|As on September \d{1,2}, \d{4}; \d{4} Hrs|\d+(?:TH|ST|ND|RD) UN GENERAL ASSEMBLY DEBATE|UN GENERAL ASSEMBLY \d{1,2}\.\d{2}|\d{1,2} SEPTEMBER \d{4}|NEW YORK, USA(?: \d+ mins)?)',line.strip(),re.I))


def source_lines(text, raw=None):
    """Recover page and blank-line metadata from cached PDF, aligning to frozen text."""
    if raw is None:
        return [dict(start=m.start(), end=m.end(), page=None, blank_before=True, text=m.group())
                for m in re.finditer(r'[^\n]+', text)]
    page_objects = PdfReader(BytesIO(raw)).pages
    pages, geometries = [], []
    for page in page_objects:
        chunks = []
        def visitor(content, cm, tm, font, size):
            clean = normalize(content)
            if clean and '\n' not in clean:
                chunks.append((clean, tm[5]))
        pages.append(page.extract_text(visitor_text=visitor))
        geometries.append({line: y for line, y in chunks if sum(t == line for t, _ in chunks) == 1})
    if normalize('\n'.join(pages)) != text:
        raise ValueError('PDF extraction no longer reproduces frozen text; pin extractor or review new source version')
    lines, offset = [], 0
    for page_no, page in enumerate(pages, 1):
        blank = False
        geometry = geometries[page_no-1]
        normalized_lines = [normalize(line) for line in page.splitlines() if normalize(line)]
        gaps = [geometry[a]-geometry[b] for a,b in zip(normalized_lines,normalized_lines[1:])
                if a in geometry and b in geometry and 4 < geometry[a]-geometry[b] < 60]
        normal_gap = median(gaps) if gaps else None
        previous = None
        for physical in page.splitlines():
            line = normalize(physical)
            if not line:
                blank = True
                continue
            if '\n' in line or text[offset:offset+len(line)] != line:
                raise ValueError('PDF physical-line alignment failed')
            gap = geometry[previous]-geometry[line] if previous in geometry and line in geometry else None
            lines.append(dict(start=offset, end=offset+len(line), page=page_no,
                              blank_before=blank, text=line,
                              geometry_paragraph_before=bool(normal_gap and gap and gap > normal_gap*1.6),
                              geometry_y=geometry.get(line)))
            offset += len(line) + 1
            blank = False
            previous = line
    if offset != len(text)+1:
        raise ValueError('PDF source coverage mismatch')
    return lines


def reading_blocks(text, lines, is_html=False, body_start=0):
    """Paragraphs use PDF blanks, measured line gaps and addresses, never pages.

    Where original layout has no blank, the paragraph boundary remains unknown.
    Sentence segmentation is independent of that uncertainty.
    """
    blocks, omitted, current = [], [], []
    speaker = None
    def flush():
        nonlocal current
        if current:
            indices = []
            for line in current:
                if indices:
                    indices.append(current_source_newline(indices[-1], text))
                indices.extend(range(line['start'], line['end']))
            blocks.append(dict(start=indices[0], end=indices[-1]+1, source_indices=indices,
                               reading_text=''.join(' ' if text[i]=='\n' else text[i] for i in indices),
                               speaker=speaker, pages=sorted({l['page'] for l in current if l['page'] is not None}),
                               paragraph_id=f"paragraph-{current[0]['start']}",
                               boundary_basis='html_block' if is_html else 'pdf_blank_or_measured_line_gap_or_address_or_document_boundary'))
            current = []
    for line in lines:
        if line['end'] <= body_start:
            omitted.append(dict(start=line['start'],end=line['end'],text=line['text'],page=line['page'],reason='front_matter_or_salutation'))
            continue
        if not is_html and layout_header_line(line['text']):
            omitted.append(dict(start=line['start'], end=line['end'], text=line['text'], page=line['page'], reason='page_or_running_header'))
            continue
        match = MARKER.match(line['text']) if is_html else None
        if match:
            flush()
            speaker = match.group()
        if current and (is_html or ((line['blank_before'] or line.get('geometry_paragraph_before')) and terminal(current[-1]['text'])) or ADDRESS.fullmatch(current[-1]['text'])):
            flush()
        current.append(line)
    flush()
    return blocks, omitted


def current_source_newline(last_index, text):
    # Synthetic reading space maps to the first actual LF after the preceding line.
    if text[last_index+1] != '\n':
        raise ValueError('Expected frozen physical line boundary')
    return last_index+1


def sentence_windows(reading):
    """Conservative English/French punctuation splitter, with titles and initials."""
    start = 0
    for match in re.finditer(r'''[.!?…]+(?:[ \t]*[”’»"')\]])*(?=\s|$)''', reading):
        end = match.end()
        if ABBREVIATIONS.search(reading[:end].rstrip("”’»\"')]")):
            continue
        # Avoid the extraction artefact '1. 3 billion' becoming two sentences.
        if re.search(r'\d\.$', reading[:end]) and re.match(r'\s*\d', reading[end:]):
            continue
        if end > start:
            yield start, end
        start = end
        while start < len(reading) and reading[start].isspace():
            start += 1
    if start < len(reading):
        yield start, len(reading)


def units(text, lines, is_html=False, body_start=0):
    blocks, omitted = reading_blocks(text, lines, is_html, body_start)
    output = []
    for block in blocks:
        windows = [(0,len(block['reading_text']))] if is_html else sentence_windows(block['reading_text'])
        for a,b in windows:
            indices = block['source_indices'][a:b]
            pages=sorted({line['page'] for line in lines if line['page'] is not None
                          and line['start'] < indices[-1]+1 and indices[0] < line['end']})
            output.append(dict(block, start=indices[0], end=indices[-1]+1,
                               source_indices=indices, reading_text=block['reading_text'][a:b],
                               pages=pages,
                               segment_kind='html_paragraph' if is_html else 'sentence'))
    return output, blocks, omitted


def actor_attribution(doc, speaker):
    if doc['actor_id'] != 'USA':
        return 'pending', []  # Source role verified, passage quotations still require review.
    if speaker in ('PRESIDENT OBAMA:', 'THE PRESIDENT:'):
        return 'pending', []
    return 'unresolved', ['attribution_actor_mismatch' if speaker else 'attribution_unknown']


def build(cache, old_batch):
    base = json.loads((cache/'records.json').read_text())
    source_review=json.loads((ROOT/'data/pilot-v1/source_review.json').read_text())
    if digest((cache/'records.json').read_bytes()) != source_review['records_sha256']:
        raise ValueError('Frozen pilot metadata differs from source review')
    original_manifest=json.loads((old_batch/'manifest.json').read_text())
    for name,sha in original_manifest['artifacts'].items():
        if digest((old_batch/name).read_bytes()) != sha:
            raise ValueError('Original annotation artifact changed: '+name)
    history = overlay_history(old_batch)
    validate_dataset(base+history, cache)
    index = {r['id']:r for r in base+history}
    docs = [r for r in base if r['record_type']=='document']
    old = [r for r in base+history if r['record_type']=='claim']
    annotations = [r for r in history if r['record_type']=='annotation']
    _, lenses = load_config()
    segmentation_config=json.loads((ROOT/'annotations/v2/segmentation_config.json').read_text())
    candidates, segments, texts, per_document = [], {}, {}, []
    for doc in docs:
        text = (cache/doc['text_path']).read_text()
        texts[doc['id']] = text
        html = doc['actor_id']=='USA'
        lines = source_lines(text, None if html else (cache/doc['raw_path']).read_bytes())
        marker=segmentation_config['pdf_body_starts'].get(doc['id'])
        if not html and (not marker or text.count(marker)!=1):
            raise ValueError('PDF requires one explicit, reviewed body-start marker')
        body_start=text.index(marker) if marker else 0
        if body_start not in {line['start'] for line in lines}:
            raise ValueError('Body marker must begin a frozen physical line')
        us, paragraphs, omitted = units(text, lines, html, body_start)
        segments[doc['id']] = dict(document_id=doc['id'], text_sha256=doc['text_sha256'],
                                  physical_lines=lines, paragraphs=paragraphs, units=us, omitted=omitted)
        relevant_old = [r for r in old if r['document_id']==doc['id']]
        event = index[doc['event_id']]
        proposals = []
        for u in us:
            for lens in lenses.values():
                if not lens['applicable_from'] <= event['event_date'] or (lens['applicable_until'] and event['event_date'] > lens['applicable_until']):
                    continue
                words = lens.get('candidate_keywords_by_language',{}).get(doc['language'],lens['candidate_keywords'])
                if any(w.casefold() in u['reading_text'].casefold() for w in words):
                    proposals.append((u,lens))
        # Retain the six explicitly reviewed windows as curated units. This preserves
        # multi-sentence attribution (B07), without pretending a new window is equivalent.
        for parent in relevant_old:
            if parent.get('revision_of'):
                positions = [i for i in range(parent['start'],parent['end'])
                             if not any(h['start']<=i<h['end'] for h in omitted)]
                # Keep this exact reviewed source envelope, including physical LF.
                proposals.append((dict(start=parent['start'],end=parent['end'],source_indices=positions,
                                       reading_text=''.join(' ' if text[i]=='\n' else text[i] for i in positions),
                                       speaker=parent['speaker'], paragraph_id=f"review-window-{parent['start']}",
                                       segment_kind='retained_review_window'), lenses[parent['lens_id']]))
        seen = set()
        for u,lens in proposals:
            key = (u['start'],u['end'],lens['id'])
            if key in seen:
                continue
            seen.add(key)
            parents = [p for p in relevant_old if p['lens_id']==lens['id'] and p['start']<u['end'] and u['start']<p['end']]
            attribution, issues = actor_attribution(doc,u['speaker'])
            if not terminal(u['reading_text']): issues.append('extraction_boundary')
            if any(u['start']<=h['start']<u['end'] for h in omitted): issues.append('extraction_header_in_envelope')
            if re.search(r'\w-\n\w',text[u['start']:u['end']]): issues.append('extraction_hyphenation')
            if doc['language']=='fr': issues.append('language_review')
            if doc['translation_provenance']: issues.append('translation_review')
            if doc['actor_id']=='EU': issues.append('EU_common_position_review')
            exact_parents = [p for p in parents if (p['start'],p['end'])==(u['start'],u['end'])]
            for p in exact_parents:
                if p['id']=='claim-revision-23300a15e6dd281d3917fffa0e6bf107a6ff83e3d4bdfa511e84d8b6614ff316': issues.append('scope_hold_W1')
                if p['id'] in {a['claim_id'] for a in annotations if a['batch_id'] in ('B09-R1','B10-R1')}: issues.append('scope_insufficiency')
            candidates.append(dict(schema_version='2.0.0',record_type='claim',
                id='claim-v2-'+digest(f"{VERSION}:{doc['id']}:{doc['text_sha256']}:{lens['id']}:{u['start']}:{u['end']}".encode()),
                document_id=doc['id'],event_id=event['id'],lens_id=lens['id'],target_text=lens['definition'],
                start=u['start'],end=u['end'],quote=text[u['start']:u['end']],text_sha256=doc['text_sha256'],
                offset_unit='unicode_code_point_half_open',speaker=u['speaker'],attribution_status=attribution,
                status='annotation_candidate',selection_method='source_aligned_sentences_v2',qualifications='Source-role, delivery and language qualifications remain in source_review.json; no scoring clearance.',
                unresolved_reason='Annotation candidate; source, scope and attribution gates remain. No machine stance prediction.',
                reading_text=u['reading_text'],source_indices=u['source_indices'],segment_kind=u['segment_kind'],
                derived_from=sorted(p['id'] for p in parents), quality_issues=sorted(set(issues)),
                paragraph_id=u['paragraph_id'],segmentation_version=VERSION))
        subset = [c for c in candidates if c['document_id']==doc['id']]
        per_document.append(dict(document_id=doc['id'],actor_id=doc['actor_id'],language=doc['language'],
                                 old_candidates=sum(r['document_id']==doc['id'] and not r.get('revision_of') for r in old),
                                 new_candidates=len(subset),source_pages=max((l['page'] or 0 for l in lines)),
                                 reconstructed_paragraphs=len(paragraphs),sentence_or_html_units=len(us),
                                 cross_page_units=sum(len(u['pages'])>1 and any(h['start']>u['start'] and h['end']<u['end'] for h in omitted) for u in us),
                                 issue_counts=dict(Counter(i for c in subset for i in c['quality_issues']))))
    candidates.sort(key=lambda c:(c['document_id'],c['start'],c['end'],c['lens_id']))
    validate_dataset(base+history+candidates,cache)
    lineage,transfers = [],[]
    for p in old:
        targets = [c for c in candidates if p['id'] in c['derived_from']]
        lineage.append(dict(old_candidate_id=p['id'],targets=[dict(candidate_id=c['id'],relationship='exact_source_evidence' if (p['start'],p['end'])==(c['start'],c['end']) else 'changed_evidence_requires_review') for c in targets],
                            disposition='mapped' if targets else 'no_v2_keyword_match_review_required',
                            annotation_overwritten=False))
    for a in annotations:
        p = index[a['claim_id']]
        for c in candidates:
            if p['id'] not in c['derived_from'] or (p['start'],p['end'],p['quote'])!=(c['start'],c['end'],c['quote']):
                continue
            # Same source, event, proposition, speaker turn and exact context window.
            # A transfer points at the original annotation; it does not mint a new vote.
            transfers.append(dict(transfer_version='1.0.0',transfer_id='transfer-'+digest(f"{a['id']}:{c['id']}".encode()),
                                  from_annotation_id=a['id'],from_candidate_id=p['id'],to_candidate_id=c['id'],
                                  source_text_sha256=c['text_sha256'],basis='identical_source_envelope_event_lens_context_and_speaker_turn',
                                  source_speaker=c['speaker'],
                                  ai_assisted=True,independent_human=False,new_independent_judgment=False,
                                  scoring_status='excluded_scope_hold_W1' if 'scope_hold_W1' in c['quality_issues'] else a['scoring_status'],
                                  retained_quality_issues=c['quality_issues']))
    return base,history,candidates,segments,lineage,transfers,per_document,texts


def validate_transfers(transfers, records):
    index = {r['id']:r for r in records}
    ids = set()
    for t in transfers:
        TRANSFER_VALIDATOR.validate(t)
        if t['transfer_id'] in ids: raise ValueError('Duplicate annotation transfer')
        ids.add(t['transfer_id'])
        a,p,c = (index[t[k]] for k in ('from_annotation_id','from_candidate_id','to_candidate_id'))
        if a['claim_id']!=p['id'] or t['independent_human'] or t['new_independent_judgment']:
            raise ValueError('Transfer cannot create independent annotations')
        if any(p[k]!=c[k] for k in ('document_id','event_id','lens_id','text_sha256','start','end','quote')):
            raise ValueError('Changed evidence cannot inherit a judgment')
        if t['source_text_sha256']!=c['text_sha256'] or t['retained_quality_issues']!=c['quality_issues']:
            raise ValueError('Transfer lost provenance or quality gates')
        if t['source_speaker'] != c['speaker'] or (p['speaker'] is not None and p['speaker'] != c['speaker']):
            raise ValueError('Transfer changed speaker attribution')
        expected_status='excluded_scope_hold_W1' if 'scope_hold_W1' in c['quality_issues'] else a['scoring_status']
        if t['scoring_status'] != expected_status:
            raise ValueError('Transfer lost the original scoring hold')


def validate_export_references(rows,records,texts):
    index={r['id']:r for r in records}
    for row in rows:
        TASK_VALIDATOR.validate(row)
        claim=index[row['candidate_id']]
        doc=index[claim['document_id']]
        event=index[claim['event_id']]
        expected=dict(document_id=doc['id'],event_id=event['id'],actor_id=doc['actor_id'],
                      event_date=event['event_date'],language=doc['language'],source_url=doc['canonical_url'],
                      attachment_url=doc['resolved_url'],text_sha256=claim['text_sha256'],
                      start=claim['start'],end=claim['end'],exact_passage=claim['quote'],
                      lens_id=claim['lens_id'],lens_proposition=claim['target_text'])
        if any(row[k]!=value for k,value in expected.items()):
            raise ValueError('Export disagrees with source/event/candidate reference')
        text=texts[doc['id']]
        if not 0 <= row['context_start'] <= row['start'] < row['end'] <= row['context_end'] <= len(text):
            raise ValueError('Export context offsets invalid')
        if (text[row['context_start']:row['start']]!=row['context_before']
                or text[row['end']:row['context_end']]!=row['context_after']):
            raise ValueError('Export context does not reproduce unchanged source')
        for identifier in row['related_candidate_ids'].split(';'):
            if identifier:
                other=index[identifier]
                if any(other[k]!=claim[k] for k in ('document_id','event_id','start','end','text_sha256')):
                    raise ValueError('Related passage is from different evidence/event')


def main():
    from .review3 import record_third_review
    cache=ROOT.parent/'.local/pilot-v1'
    batch=ROOT.parent/'.local/annotation-v1'
    record_third_review(cache,batch)
    base,history,claims,segments,lineage,transfers,counts,texts=build(cache,batch)
    validate_transfers(transfers,base+history+claims)
    output=ROOT.parent/'.local/annotation-v2'
    output.mkdir(parents=True,exist_ok=True)
    for name,value in [('candidates.json',claims),('segments.json',segments),('lineage.json',lineage),('annotation_transfers.json',transfers)]:
        write_immutable(output/name,value)
    # Every v2 task remains blank. Annotation reuse is represented only by transfers.
    index={r['id']:r for r in base+history+claims}
    rows=[]
    for i,c in enumerate(claims,1):
        related=[p['id'] for p in claims if p['document_id']==c['document_id'] and (p['start'],p['end'])==(c['start'],c['end']) and p['id']!=c['id']]
        row=task(index[c['document_id']],index[c['event_id']],c,texts[c['document_id']],f'V2-{i:03}',related)
        # Whole neighboring units provide context, bounded by the same speaker turn.
        neighbors=segments[c['document_id']]['units']
        before=[u for u in neighbors if u['end'] <= c['start'] and u['speaker']==c['speaker']][-2:]
        after=[u for u in neighbors if u['start'] >= c['end'] and u['speaker']==c['speaker']][:2]
        # Do not jump over a different speaker and retrieve distant same-speaker text.
        intervening=[u for u in neighbors if (before and before[0]['start'] <= u['start'] < c['start']) or (after and c['end'] <= u['start'] <= after[-1]['start'])]
        if any(u['speaker']!=c['speaker'] for u in intervening):
            before=[]
            after=[]
        context_start=before[0]['start'] if before else c['start']
        context_end=after[-1]['end'] if after else c['end']
        text=texts[c['document_id']]
        row.update(context_start=context_start,context_end=context_end,
                   context_before=text[context_start:c['start']],context_after=text[c['end']:context_end])
        TASK_VALIDATOR.validate(row)
        rows.append(row)
    write_rows(output/'queue',rows)
    for suffix in ('.csv','.jsonl'):
        exported=read_rows(output/('queue'+suffix))
        validate_rows(exported,rows)
        validate_export_references(exported,base+history+claims,texts)
    report=dict(segmentation_version=VERSION,old_original_candidates=184,old_manual_revisions=6,
                new_candidates=len(claims),distinct_new_passages=len({(c['document_id'],c['start'],c['end']) for c in claims}),
                exact_annotation_transfers=len(transfers),unchanged_events=10,per_document=counts,
                independent_annotation_count=0,issue_counts=dict(Counter(i for c in claims for i in c['quality_issues'])),
                changed_evidence_annotation_policy='No transfer. New human review required.',
                paragraph_limit='PDF blank lines, unique-line vertical gaps (>1.6 median line spacing) and addresses recovered from cached bytes. Unmatched/ambiguous geometry has uncertain paragraph boundaries; pages never force sentence/paragraph cuts.',
                ambiguity_policy='Scope, attribution and extraction flags are separate. Political ambiguity is not inferred; model ambiguity is not evaluated.',
                artifact_hashes={p.name:digest(p.read_bytes()) for p in output.iterdir() if p.is_file() and p.name not in ('report.json','manifest.json','next_five.csv','next_five.jsonl','sample_audit.json')})
    write_immutable(output/'report.json',report)
    write_immutable(ROOT/'annotations/v2/segmentation_report.json',report)
    prepare_review_artifacts(output,base,claims,segments,rows,transfers,report)
    print(json.dumps({k:report[k] for k in ('new_candidates','distinct_new_passages','exact_annotation_transfers','issue_counts')},indent=2))

def prepare_review_artifacts(output,base,claims,segments,rows,transfers,report):
    spec=json.loads((ROOT/'annotations/v2/next_five_selection.json').read_text())
    by_id={c['id']:c for c in claims}
    transferred={t['to_candidate_id'] for t in transfers}
    next_rows=[]
    for item in spec['items']:
        matches=[r for r in rows if (r['document_id'],r['start'],r['lens_id'])==(item['document_id'],item['start'],item['lens_id'])]
        if len(matches)!=1: raise ValueError('Review selection no longer uniquely matches source')
        row=dict(matches[0],row_id=item['row_id'])
        candidate=by_id[row['candidate_id']]
        if row['candidate_id'] in transferred or any(i.startswith(('extraction','attribution')) for i in candidate['quality_issues']):
            raise ValueError('Next review requires unreviewed evidence with clean extraction and speaker boundaries')
        next_rows.append(row)
    write_rows(output/'next_five',next_rows)
    for suffix in ('.csv','.jsonl'):validate_rows(read_rows(output/('next_five'+suffix)),next_rows)
    audit=[]
    notes={
        'doc-eu-unga77':'Sentence boundaries restored using measured PDF line gaps; reviewed B07 multi-sentence window retained separately. EU common-position review remains.',
        'doc-eu-unga78':'Original French retained. Repeated page numbers masked only in mapped reading view. No translation or language clearance.',
        'doc-ind-unga77':'Page-spanning continuation checked. UN General Assembly body line retained. Visible continue s / Th ose / respon ds artefacts need visual source comparison; not silently corrected.',
        'doc-ind-unga78':'Sentence reflow checked. Generic territorial-integrity wording remains subject to exact-target review.',
        'doc-tur-unga77':'UNOFFICIAL TRANSLATION retained; original Turkish absent. Spacing such as settlemen t / regi on remains in source; no correction inferred.',
        'doc-tur-unga78':'Courtesy Translation / Check against delivery retained. Turkish original absent; word spacing and delivery qualification remain.',
        'doc-us2014':'Presidential turns retained; Yatsenyuk turns are separate and held from US scoring.',
        'doc-us2022':'HTML paragraphs retained. Reporter turns remain held; three interrupted utterances remain explicitly flagged.',
        'doc-zaf-unga77':'Page-boundary continuation checked with raw envelope preserved. Prepared-statement delivery qualification remains.',
        'doc-zaf-unga78':'Repeated V7/date/location headers masked in reading view; territorial-integrity statement remains scope-review evidence.'}
    for doc in [r for r in base if r['record_type']=='document']:
        pool=[c for c in claims if c['document_id']==doc['id'] and not any(i.startswith(('extraction','attribution')) for i in c['quality_issues'])]
        selected=[pool[0],pool[-1]]
        # Include every candidate whose exact envelope crosses a removed page header.
        selected += [c for c in claims if c['document_id']==doc['id'] and 'extraction_header_in_envelope' in c['quality_issues']]
        for c in selected:
            audit.append(dict(candidate_id=c['id'],document_id=doc['id'],actor_id=doc['actor_id'],language=doc['language'],
                              start=c['start'],end=c['end'],reading_text=c['reading_text'],quality_issues=c['quality_issues'],
                              audit_origin='assistant_source_and_segmentation_review_not_independent_annotation',
                              exact_alignment_checked=True,stance_label_assigned=False,review_notes=notes[doc['id']]))
    write_immutable(output/'sample_audit.json',audit)
    write_immutable(ROOT/'annotations/v2/sample_audit_summary.json',dict(
        sample_count=len(audit),actors=sorted({a['actor_id'] for a in audit}),languages=sorted({a['language'] for a in audit}),
        origin='assistant diagnostic source/segmentation review; no independent judgments or stance labels',
        per_document_notes=notes,private_detail_path='.local/annotation-v2/sample_audit.json'))
    public_mapping=[dict(row_id=r['row_id'],candidate_id=r['candidate_id'],document_id=r['document_id'],event_id=r['event_id'],
                         start=r['start'],end=r['end'],lens_id=r['lens_id'],text_sha256=r['text_sha256']) for r in next_rows]
    write_immutable(ROOT/'annotations/v2/next_five_manifest.json',dict(version='annotation-v2-batch-1',items=public_mapping,
        source_rights='Metadata only. Passages and complete tasks remain private.',labels='All blank; no machine suggestions.'))
    write_immutable(output/'manifest.json',dict(version=VERSION,report_sha256=digest((output/'report.json').read_bytes()),
        next_five=public_mapping,
        artifacts={p.name:digest(p.read_bytes()) for p in output.iterdir() if p.is_file() and p.name!='manifest.json'},
        private_storage='Full source/excerpts remain local and private; source-rights and fresh-machine restoration remain unconfirmed.'))


if __name__=='__main__': main()
