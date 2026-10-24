"""Record reviewed v2 tasks and prepare five retrieved plus five retained controls."""
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from .annotations import read_rows, write_rows, task, validate_rows, HUMAN_FIELDS
from .collect import utcnow
from .followup import overlay_history
from .reviewed import write_immutable
from .resegment import actor_attribution, validate_export_references
from .segmentation import terminal
from .validation import ROOT, digest, load_config, validate_dataset

QUALITY_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT/'schemas/review-v1/quality_assessment.schema.json').read_text()))
SOURCE_FLAGS = {'EU_common_position_review', 'language_review', 'translation_review'}


def validate_quality(assessments, records):
    index = {r['id']: r for r in records}
    seen = set()
    for assessment in assessments:
        QUALITY_VALIDATOR.validate(assessment)
        if assessment['assessment_id'] in seen:
            raise ValueError('Duplicate quality assessment')
        seen.add(assessment['assessment_id'])
        annotation = index[assessment['annotation_id']]
        candidate = index[assessment['candidate_id']]
        if annotation['claim_id'] != candidate['id'] or candidate['text_sha256'] != assessment['source_text_sha256']:
            raise ValueError('Assessment provenance differs from annotation/evidence')
        expected_source = sorted(set(candidate['quality_issues']) & SOURCE_FLAGS)
        expected_evidence = sorted(set(candidate['quality_issues']) - SOURCE_FLAGS - {'scope_insufficiency','scope_hold_W1'})
        if assessment['source_eligibility_flags'] != expected_source or assessment['evidence_quality_flags'] != expected_evidence:
            raise ValueError('Assessment cleared an existing source/evidence flag')
        if assessment['language_review'].startswith('assisted_French') and index[candidate['document_id']]['language'] != 'fr':
            raise ValueError('French review attached to non-French evidence')
        if annotation['batch_id'] == 'V2-B05' and assessment['scope_flags'] != ['scope_insufficiency']:
            raise ValueError('Strict territorial scope exclusion must survive')


def record_review(cache, v1, v2):
    base = json.loads((cache/'records.json').read_text())
    old_history = overlay_history(v1)
    candidates = json.loads((v2/'candidates.json').read_text())
    records = base + old_history + candidates
    folder = ROOT/'annotations/v2/reviews/Badr_A'
    submission_path = folder/'submission-0004.json'
    submission = json.loads(submission_path.read_text())
    path = folder/'review-0004.review.json'
    private = v2/'reviews/Badr_A/review-0004'
    source_rows = read_rows(v2/'next_five.jsonl')
    manifest = json.loads((v2/'manifest.json').read_text())
    for name, sha in manifest['artifacts'].items():
        if digest((v2/name).read_bytes()) != sha:
            raise ValueError('V2 input artifact changed: '+name)
    mapping = {r['row_id']:r for r in source_rows}
    if submission['ai_assisted'] is not True or submission['independent_human'] is not False or submission['annotator_id'] != 'Badr_A':
        raise ValueError('Reviewed assisted non-independent provenance required')
    if len(submission['judgments']) != 5 or {j['batch_id'] for j in submission['judgments']} != set(mapping):
        raise ValueError('Judgments must match the five frozen v2 task IDs')
    if path.exists():
        ledger = json.loads(path.read_text())
        if ledger['submission_sha256'] != digest(submission_path.read_bytes()):
            raise ValueError('Cannot overwrite reviewed history')
        annotations = json.loads((private/'overlay_records.json').read_text())
        assessments = json.loads((private/'quality_assessments.json').read_text())
        if ledger['annotations'] != annotations or ledger['quality_assessments'] != assessments:
            raise ValueError('Public ledger and private history disagree')
        validate_dataset(records+annotations,cache)
        validate_quality(assessments,records+annotations)
        return records+annotations, assessments
    index = {r['id']:r for r in records}
    now = utcnow()
    annotations, assessments = [], []
    returned = []
    for judgment in submission['judgments']:
        row = mapping[judgment['batch_id']]
        candidate = index[row['candidate_id']]
        annotation = dict(schema_version='1.2.0',record_type='annotation',
            id='annotation-'+digest(f"Badr_A:review-0004:{candidate['id']}:{digest(submission_path.read_bytes())}".encode()),
            claim_id=candidate['id'],batch_id=row['row_id'],origin='ai_assisted_reviewed',annotator_id='Badr_A',
            codebook_version=row['codebook_version'],label=judgment['label'],review_status='reviewed_non_independent',
            created_at=now,rationale=judgment['review_notes'],review_notes=judgment['review_notes'],supersedes=None,
            review_provenance=submission['review_provenance'],ai_assisted=True,independent_human=False,
            scoring_status='not_scored_pending_quality_review')
        scope = ['scope_insufficiency'] if row['row_id']=='V2-B05' else []
        assessment = dict(schema_version='1.0.0',record_type='review_quality_assessment',
            assessment_id='quality-'+digest(annotation['id'].encode()),annotation_id=annotation['id'],candidate_id=candidate['id'],
            review_id='review-0004',source_text_sha256=candidate['text_sha256'],
            source_eligibility_flags=sorted(set(candidate['quality_issues']) & SOURCE_FLAGS),
            evidence_quality_flags=sorted(set(candidate['quality_issues']) - SOURCE_FLAGS - {'scope_insufficiency','scope_hold_W1'}),
            scope_flags=scope,directional_scoring_eligible=False,
            scope_reason=judgment['review_notes'] if scope else 'No new scope determination; existing source and evidence gates remain.',
            language_review='assisted_French_review_not_independent_language_validation' if row['language']=='fr' else 'not_newly_reviewed')
        annotations.append(annotation)
        assessments.append(assessment)
        returned.append(dict(row,label=annotation['label'],annotator_id='Badr_A',review_status='needs_adjudication',review_notes=annotation['review_notes']))
    validate_dataset(records+annotations,cache)
    validate_quality(assessments,records+annotations)
    validate_rows(returned,source_rows)
    write_immutable(private/'overlay_records.json',annotations)
    write_immutable(private/'quality_assessments.json',assessments)
    write_rows(private/'reviewed_next_five',returned)
    prior = ROOT/'annotations/v1/reviews/Badr_A/review-0003.review.json'
    write_immutable(path,dict(review_id='review-0004',recorded_at=now,annotator_id='Badr_A',
        submission_sha256=digest(submission_path.read_bytes()),previous_review_sha256=digest(prior.read_bytes()),
        annotations=annotations,quality_assessments=assessments,independent_annotation_count=0,
        history_policy='Append only. Stance, source eligibility and evidence quality are separate. No original flags cleared.'))
    return records+annotations, assessments


def family_summary(records, transfers, assessments):
    index = {r['id']:r for r in records}
    equivalents = {t['to_candidate_id']:t['from_candidate_id'] for t in transfers}
    def root(identifier):
        visited = set()
        while identifier in equivalents or index[identifier].get('revision_of'):
            if identifier in visited: raise ValueError('Circular review lineage')
            visited.add(identifier)
            identifier = equivalents.get(identifier) or index[identifier]['revision_of']
        return identifier
    annotations = [r for r in records if r['record_type']=='annotation']
    current = {}
    for annotation in annotations:
        current[root(annotation['claim_id'])] = annotation
    counts = Counter(a['label'] for a in current.values())
    unresolved = [dict(annotation_id=a['id'],batch_id=a['batch_id'],reason_class='scope_insufficiency',review_notes=a['review_notes'])
                  for a in current.values() if a['label']=='unresolved']
    if {u['batch_id'] for u in unresolved} != {'B09-R1','B10-R1','V2-B05'}:
        raise ValueError('New unresolved reasons require explicit classification')
    return dict(summary_version='review-summary-1.0.0',historical_decisions=len(annotations),
        historical_label_counts=dict(Counter(a['label'] for a in annotations)),
        current_review_families=len(current),current_label_counts=dict(counts),
        resolved_stance_labels=sum(counts[k] for k in ('support','oppose','no_stance','mixed')),
        resolved_binary_direction_labels=counts['support']+counts['oppose'],unresolved_reasons=unresolved,
        additional_scope_held_support=dict(batch_id='B05-R1',rule='W1',directional_scoring_eligible=False),
        independent_annotations=0,scored_claims=0,
        counting_policy='Collapse manual revisions and exact-evidence transfer aliases; take latest reviewed judgment per family. Distinct lenses remain distinct tasks. Old defective judgments remain historical, not extra votes.')


def repair_control(original, doc, event, text, segments, lenses):
    overlapping = [u for u in segments['units'] if u['start'] < original['end'] and original['start'] < u['end']]
    if not overlapping:
        raise ValueError('Control has no complete sentence window')
    start, end = overlapping[0]['start'], overlapping[-1]['end']
    if not start <= original['start'] < original['end'] <= end:
        raise ValueError('Control repair must preserve its original sampled span')
    speakers = {u['speaker'] for u in overlapping}
    if len(speakers)!=1:
        raise ValueError('Control expansion crossed speakers')
    speaker = next(iter(speakers))
    attribution, flags = actor_attribution(doc,speaker)
    if flags or not terminal(text[start:end]):
        raise ValueError('Control expansion is not ready for clean review')
    omitted = segments['omitted']
    if any(start < h['start'] < end for h in omitted):
        raise ValueError('Header-crossing control needs separate boundary review')
    if doc['language']=='fr':flags.append('language_review')
    if doc['actor_id']=='EU':flags.append('EU_common_position_review')
    if doc['translation_provenance']:flags.append('translation_review')
    identifier='claim-control-v2-'+digest(f"{original['candidate_id']}:{doc['text_sha256']}:{start}:{end}".encode())
    return dict(schema_version='2.0.0',record_type='claim',id=identifier,document_id=doc['id'],event_id=event['id'],
        lens_id=original['lens_id'],target_text=lenses[original['lens_id']]['definition'],start=start,end=end,quote=text[start:end],
        text_sha256=doc['text_sha256'],offset_unit='unicode_code_point_half_open',speaker=speaker,attribution_status=attribution,
        status='annotation_candidate',selection_method='source_aligned_sentences_v2',qualifications=doc['translation_provenance'],
        unresolved_reason='Random retrieval-audit control; no stance label assigned.',reading_text=text[start:end].replace('\n',' '),
        source_indices=list(range(start,end)),segment_kind='retained_review_window',derived_from=[],quality_issues=flags,
        paragraph_id='control-window-'+str(start),segmentation_version='orbit-segmentation-2.0.0')


def prepare_batch(cache,v1,v2,records):
    out = v2/'batch-0002'
    index = {r['id']:r for r in records}
    candidates = json.loads((v2/'candidates.json').read_text())
    segments = json.loads((v2/'segments.json').read_text())
    texts = {r['id']:(cache/r['text_path']).read_text() for r in records if r['record_type']=='document'}
    retrieved = read_rows(v2/'queue.jsonl')
    transferred = {t['to_candidate_id'] for t in json.loads((v2/'annotation_transfers.json').read_text())}
    reviewed = {r['claim_id'] for r in records if r['record_type']=='annotation'} | transferred
    selection = [('doc-us2014',1364,'territorial_recognition'),('doc-eu-unga77',3229,'sanctions'),
                 ('doc-tur-unga78',8136,'territorial_recognition'),('doc-ind-unga78',9217,'territorial_recognition'),
                 ('doc-zaf-unga77',7478,'invasion_responsibility')]
    tasks = []
    for n,key in enumerate(selection,6):
        matches=[r for r in retrieved if (r['document_id'],r['start'],r['lens_id'])==key]
        if len(matches)!=1:raise ValueError('Retrieved selection is ambiguous')
        row=dict(matches[0],row_id=f'V2-B{n:02}')
        candidate=index[row['candidate_id']]
        if candidate['id'] in reviewed or any(i.startswith(('extraction','attribution')) for i in candidate['quality_issues']):
            raise ValueError('Retrieved task already reviewed or extraction/attribution held')
        tasks.append(row)
    _,lenses=load_config()
    original_manifest=json.loads((v1/'manifest.json').read_text())
    if digest((v1/'first_batch.jsonl').read_bytes()) != original_manifest['artifacts']['first_batch.jsonl']:
        raise ValueError('Original seeded-control batch changed')
    original_controls=[r for r in read_rows(v1/'first_batch.jsonl') if r['selection_kind']=='nonretrieved_random_control']
    if len(original_controls)!=5:raise ValueError('Preserve all five original controls')
    controls, lineage=[],[]
    for number,original in enumerate(original_controls,11):
        doc=index[original['document_id']]
        event=index[original['event_id']]
        text=texts[doc['id']]
        control=repair_control(original,doc,event,text,segments[doc['id']],lenses)
        row=task(doc,event,dict(control,selection_kind='nonretrieved_random_control'),text,f'V2-B{number:02}',[])
        # Use complete surrounding sentence units, not line-cut context.
        before=[u for u in segments[doc['id']]['units'] if u['end']<=control['start'] and u['speaker']==control['speaker']][-2:]
        after=[u for u in segments[doc['id']]['units'] if u['start']>=control['end'] and u['speaker']==control['speaker']][:2]
        a=before[0]['start'] if before else control['start']
        b=after[-1]['end'] if after else control['end']
        row.update(context_start=a,context_end=b,context_before=text[a:control['start']],context_after=text[control['end']:b])
        words=lenses[control['lens_id']].get('candidate_keywords_by_language',{}).get(doc['language'],lenses[control['lens_id']]['candidate_keywords'])
        lineage.append(dict(row_id=row['row_id'],original_row_id=original['row_id'],original_candidate_id=original['candidate_id'],
            candidate_id=control['id'],document_id=doc['id'],event_id=event['id'],lens_id=control['lens_id'],
            text_sha256=doc['text_sha256'],original_start=original['start'],original_end=original['end'],
            revised_start=control['start'],revised_end=control['end'],
            original_selection='seeded_random_nonretrieved_v1_line_control',original_seed=20261023,
            selection_preserved=True,new_random_draw=False,annotation_transferred=False,
            current_window_keyword_match_for_assigned_lens=any(w.casefold() in control['reading_text'].casefold() for w in words),
            expansion_policy='Smallest complete source-aligned sentence/HTML-unit envelope containing original sampled line. No resampling or relabeling.'))
        controls.append(control)
        tasks.append(row)
    validate_dataset(records+controls,cache)
    validate_export_references(tasks,records+controls,texts)
    validate_rows(tasks,tasks)
    if any(r[k] for r in tasks for k in HUMAN_FIELDS):raise ValueError('New human-label fields must remain empty')
    write_immutable(out/'control_records.json',controls)
    write_immutable(out/'control_lineage.json',lineage)
    write_immutable(out/'original_controls.json',original_controls)
    write_rows(out/'next_ten',tasks)
    for suffix in ('.csv','.jsonl'):
        exported=read_rows(out/('next_ten'+suffix))
        validate_rows(exported,tasks)
        validate_export_references(exported,records+controls,texts)
    manifest=dict(batch_version='annotation-v2-batch-2',retrieved_candidates=5,random_controls=5,
        random_control_policy='Original actor-stratified seeded v1 selections retained and expanded to complete units; no new draw. Expanded windows may change retrieval status, reported per control.',
        original_batch_sha256=digest((v1/'first_batch.jsonl').read_bytes()),
        items=[dict(row_id=r['row_id'],candidate_id=r['candidate_id'],selection_kind=r['selection_kind'],document_id=r['document_id'],
                    event_id=r['event_id'],lens_id=r['lens_id'],start=r['start'],end=r['end'],text_sha256=r['text_sha256']) for r in tasks],
        control_lineage=lineage,independent_annotations=0,
        artifact_hashes={p.name:digest(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'})
    write_immutable(out/'manifest.json',manifest)
    write_immutable(ROOT/'annotations/v2/batch-0002/manifest.json',manifest)
    return tasks, controls


def main():
    cache=ROOT.parent/'.local/pilot-v1'
    v1=ROOT.parent/'.local/annotation-v1'
    v2=ROOT.parent/'.local/annotation-v2'
    records,assessments=record_review(cache,v1,v2)
    summary=family_summary(records,json.loads((v2/'annotation_transfers.json').read_text()),assessments)
    write_immutable(ROOT/'annotations/v2/reviews/Badr_A/review-0004.summary.json',summary)
    tasks,controls=prepare_batch(cache,v1,v2,records)
    print(json.dumps(dict(validated_records=len(records)+len(controls),current_label_counts=summary['current_label_counts'],
                         historical_decisions=summary['historical_decisions'],next_batch=len(tasks),random_controls=5),indent=2))

if __name__=='__main__':main()
