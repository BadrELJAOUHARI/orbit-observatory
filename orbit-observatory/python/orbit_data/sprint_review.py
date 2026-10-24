"""Strict post-acquisition gates, connected split protection and one assisted packet.

Does not read historical evaluation text or alter historical labels. Suggestions are
transparent deterministic rules, not a trained classifier or independent annotation.
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from .acquisition_sprint import OUT, Sprint, ANCHOR, RUSSIA
from .validation import ROOT, digest
from .collect import write_json, utcnow
from .workflow import write_csv, QUALITY_RESPONSE_OPTIONS
from .development_review import render

PACKET = ROOT.parent / '.local/development-review-sprint-v1'
RULE_VERSION = 'sprint-admission-suggestions-1.0.0'

def checkpoint_csv(path,rows):
    """Derived acquisition exports can advance; keep previous bytes for audit."""
    if path.exists():
        history=OUT/'export_history';history.mkdir(exist_ok=True)
        (history/(digest(path.read_bytes())+'-'+path.name)).write_bytes(path.read_bytes())
    temp=path.with_name(path.name+'.pending')
    if temp.exists():temp.unlink()
    write_csv(temp,rows);temp.replace(path)

def compact(text):
    return re.sub(r'\W+', ' ', text.casefold()).strip()

class Groups:
    def __init__(self, ids): self.parent = {x:x for x in ids}
    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]; x = self.parent[x]
        return x
    def union(self, a, b):
        a,b=self.find(a),self.find(b)
        self.parent[max(a,b)]=min(a,b)

def metadata_and_groups(docs):
    """New source text only; previous reserved relationships use metadata only."""
    old=[]
    for name in ('expansion-v6/cleared_catalog.json','pilot-v1/records.json'):
        old += [d for d in json.loads((OUT.parent/name).read_text())
                if d.get('record_type') in ('document','expansion_document')]
    old_urls={d[k].rstrip('/'):d for d in old for k in ('url','canonical_url','resolved_url','pdf_url') if d.get(k)}
    prior_clearances={}
    for p in (OUT.parent/'source-clearance-20261024').glob('*metadata.json'):
        m=json.loads(p.read_text());prior_clearances[m['requested_url']]=m
    old_split=json.loads((OUT.parent/'experimental-baseline-v2/leakage_groups.json').read_text())
    groups=Groups([d['id'] for d in docs]);seen={}; links=[]
    for d in docs:
        m=d['source_receipt'];raw=OUT/m['raw_path']
        if not raw.exists() or digest(raw.read_bytes())!=m['raw_sha256']:raise ValueError('Missing/corrupt original '+d['id'])
        if d.get('landing_receipt'):
            lm=d['landing_receipt']
            if digest((OUT/lm['raw_path']).read_bytes())!=lm['raw_sha256']:raise ValueError('Changed official UN landing receipt')
        text=(OUT/d['text_path']).read_text()
        if digest(text.encode())!=d['text_sha256']:raise ValueError('Changed source text')
        d['new_source_document']=d['canonical_url'].rstrip('/') not in old_urls and d['canonical_url'] not in prior_clearances
        match=old_urls.get(d['canonical_url'].rstrip('/'))
        if not match:
            match=next((o for o in old if o['actor_id']==d['actor_id'] and o.get('event_date')==d['event_date']
                        and re.search(r'General Assembly|UNGA|General Debate',d['title'],re.I)),None)
        if match:
            d['previous_event_id']=match['event_id'];d['new_source_document']=False
            if old_split['event_groups'].get(match['event_id']) in old_split['reserved_leakage_group_ids']:
                d['event_role']='evaluation_reserved'
        if d['source_type']=='govuk':
            p=json.loads(raw.read_text());details=p.get('details',{})
            people=p.get('links',{}).get('people',[])
            orgs=p.get('links',{}).get('organisations',[])
            d['speaker']=' / '.join(x['title'] for x in people) or d['issuer']
            d['speaker_basis']='Official GOV.UK content API people/organisation metadata; institutional text; third-party quotations remain held'
            if orgs:d['issuer']=' / '.join(x['title'] for x in orgs)
            delivered=details.get('delivered_on','')
            if delivered and re.match(r'^20\d\d-\d\d-\d\d',delivered):
                d['original_index_date']=d['event_date'];d['event_date']=delivered[:10];d['date_basis']='Official speech delivered_on metadata'
            else:d['date_basis']='Official first-publication date; communication publication event, delivery date not asserted'
        elif d['source_type']=='un':d['date_basis']='Delivery date verified from official UN delegation heading; publication date unavailable'
        else:d['date_basis']='Dated official archive entry/title/adopted-document cover; publication date separate'
        d['source_clearance_basis']='Official institutional body and permitted public endpoint; original bytes/hash retained; quoted speakers and joint signatories gated separately'
        # Group same-institution/day releases conservatively. Different speeches can
        # still be separate event records, but are not independent validation units.
        keys=[('hash',compact(text)),('day',d['actor_id'],d['event_date'],d['issuer'])]
        # Exact 80-word shingles detect overlapping passages and copied boilerplate.
        # Conservative grouping is intentional: no repeated evidence crosses splits.
        words=compact(text).split()
        keys += [('overlap',digest(' '.join(words[i:i+80]).encode())) for i in range(max(0,len(words)-79))]
        for key in keys:
            if key in seen:
                if groups.find(d['id'])!=groups.find(seen[key]):links.append(dict(a=d['id'],b=seen[key],basis=key[0]))
                groups.union(d['id'],seen[key])
            else:seen[key]=d['id']
    reserved={groups.find(d['id']) for d in docs if d['event_role']=='evaluation_reserved'}
    for d in docs:
        d['leakage_group_id']='sprint-group-'+digest(groups.find(d['id']).encode())[:24]
        if groups.find(d['id']) in reserved:d['event_role']='evaluation_reserved'
    write_json(OUT/'split_group_links.json',links)
    write_json(OUT/'split_assignments.json',{d['id']:dict(event_id=d['event_id'],group_id=d['leakage_group_id'],role=d['event_role'],previous_event_id=d.get('previous_event_id')) for d in docs})
    return docs

def extra_gates(r,doc):
    p=r['exact_passage'];s=re.sub(r'\s+',' ',p).strip();flags=[];reject=None
    if not re.search(r'[.!?][”"\')\]]?\s*$',s):flags.append('incomplete_sentence_boundary')
    if re.search(r'^(?:Read (?:the|more)|Click |For more information|View |See (?:the|also)|Related |Download )',s,re.I):reject='link_or_navigation_not_policy_statement'
    if doc['source_type']=='council' and (re.search(r'^EUCO |^EN\b|^Conclusions\s*[–-]',s) or not re.search(r'\b(?:European (?:Council|Union)|Council|EU|Russia|Ukraine)\b.{0,120}\b(?:condemns|calls|reiterates|agrees|will|must|shall|welcomes|supports|invites|remains|underlines|demands|is|has|should|takes|recalls|stresses|reaffirms|urges|recognises|recognizes)',s,re.I)):
        flags.append('PDF_cover_or_sentence_review')
    if r['lens_id']=='sanctions':
        # Local context cannot borrow a Ukraine anchor from a later unrelated item.
        prev=r['context_before'].strip().split('\n')[-1]
        if not ANCHOR.search(p) and not (ANCHOR.search(prev) and RUSSIA.search(prev)):
            flags.append('Ukraine_sanctions_basis_not_local')
        if re.search(r'Zimbabwe|DPRK|North Korea|Iran|Sudan|Middle East',p,re.I) and not (ANCHOR.search(p) and re.search(r'(?:war|invasion|aggress|annex|occupation|Ukrain).{0,130}(?:sanction|restrict|designat)|(?:sanction|restrict|designat).{0,130}(?:war|invasion|aggress|annex|occupation|Ukrain)',s,re.I)):
            flags.append('sanctions_target_or_conflict_basis_review')
    if r['lens_id']=='military_assistance' and re.search(r'^Ukraine.s critical export transportation needs',s):flags.append('incomplete_sentence_boundary')
    if r['lens_id']=='troop_withdrawal' and not re.search(r'internationally (?:recogni[sz]ed)|1991|(?:all|entire|whole|entirety).{0,35}(?:Ukrainian territory|territory of Ukraine|of Ukraine)|including.{0,30}Crimea',s,re.I):
        flags.append('W1_legal_territorial_extent_review')
    # Glued anchor words are a real extraction qualification, not political ambiguity.
    if re.search(r'(?:fullOFAC|\d{4}pursuant|astatement|FactSheet|[a-z]https?://)',p):flags.append('inline_word_boundary_extraction')
    if doc.get('previous_event_id') or not doc['new_source_document']:flags.append('previously_collected_source_not_new')
    return sorted(set(flags)),reject

def suggest(r):
    """Literal cues with an uncertainty fallback; never human approval."""
    p=re.sub(r'\s+',' ',r['exact_passage']);lens=r['lens_id']
    if re.search(r'\b(?:if|unless|provided that|only if|subject to)\b',p,re.I):
        return 'unresolved','Conditional formulation needs review against the complete proposition; no polarity inferred from its condition.'
    if lens=='sanctions':
        if re.search(r'\b(?:oppose|reject|against|lift|remove|end)\b.{0,45}(?:sanctions|restrictive measures)',p,re.I):
            return 'unresolved','Mentions opposition/removal of restrictions; verify speaker, affected measures and conditions before assigning opposition.'
        # A noun such as "sanctions" or "the imposition" is not an endorsement.
        cue=re.search(r'\b(?:we|OFAC|Treasury|United States|United Kingdom|European Council|European Union|Council|UK|government)\b.{0,60}\b(?:impos\w*|issu\w*|adopt\w*|expand\w*|maintain\w*|extend\w*|enforc\w*|designat\w*|sanction\w*|target\w*|welcom\w*|strengthen\w*|introduc\w*|support\w*|calls for)\b',p,re.I)
        if cue:return 'support','Institution describes or endorses its Russia/Ukraine restrictions: “'+cue.group().strip()+'”. Check legal implementation versus policy endorsement.'
        return 'unresolved','Russia/Ukraine sanctions are discussed, but an explicit endorsement or rejection is not established by the literal rules.'
    if lens=='invasion_responsibility':
        if re.search(r'\b(?:not|no|never)\b.{0,25}(?:invasion|aggression|unprovoked)|invasion.{0,20}\bnot\b',p,re.I):
            return 'unresolved','Negated attribution/aggression wording requires scope and speaker review; polarity is not inferred from the keyword.'
        if re.search(r'provoked|NATO.{0,50}(?:caused|responsib)|not.{0,30}Russia',p,re.I) and not re.search(r'unprovoked',p,re.I):
            return 'unresolved','Potential justification or responsibility qualification requires contextual human review.'
        cue=re.search(r'(?:Russia(?:n|’s|\x27s)?|Putin(?:’s|\x27s)?|Kremlin).{0,100}(?:inva\w*|aggress\w*|war)|(?:inva\w*|aggress\w*).{0,60}(?:Russia|Putin|Kremlin)',p,re.I)
        if cue:return 'support','Explicitly attributes the invasion/aggression/war to Russia or its leadership: “'+cue.group()[:170]+'”. Verify initiation of the February 2022 invasion, rather than an individual incident.'
        return 'unresolved','Relevant attribution wording needs manual interpretation of who initiated the full-scale invasion.'
    if lens=='military_assistance':
        if re.search(r'will not|refus|suspend|cease|stop|oppos',p,re.I):return 'unresolved','Potential refusal, restriction or suspension; its assistance type and scope require review.'
        return 'support','Explicit assistance/training/equipment provision or endorsement for Ukraine; preserve the stated type, recipient and limitations.'
    if lens=='troop_withdrawal':
        return 'support','Explicit Russian withdrawal wording passes the conservative comprehensive-scope W1 cue; confirm territorial and conditional scope in context.'
    return 'support','Both comprehensive territorial scope and annexation/non-recognition wording occur; review the strict compound territorial target without broadening it.'

def build():
    s=Sprint();s.export()
    docs=metadata_and_groups(s.docs());bydoc={d['id']:d for d in docs}
    source=[]
    for name in ('clean','held','evaluation'):source+=json.loads((OUT/(name+'.json')).read_text())
    clean=[];held=[];evaluation=[];rejected=json.loads((OUT/'rejected.json').read_text());seen={};copy=[]
    for r in source:
        d=bydoc[r['document_id']]
        for field in ('event_role','event_date','speaker','issuer','leakage_group_id','source_clearance_basis','date_basis','new_source_document'):
            r[field]=d[field]
        flags,reject=extra_gates(r,d);r['quality_flags']=sorted(set(r['quality_flags']+flags))
        text=(OUT/d['text_path']).read_text()
        assert text[r['start']:r['end']]==r['exact_passage']
        r['policy_evidence_form']='legal_implementation' if r['lens_id']=='sanctions' and re.search(r'\bdesignat(?:ed|ing|ion)\b',r['exact_passage'],re.I) else 'institutional_statement'
        if reject:rejected.append(dict(candidate_id=r['candidate_id'],document_id=d['id'],start=r['start'],end=r['end'],lens_id=r['lens_id'],reason=reject));continue
        key=(r['lens_id'],compact(r['exact_passage']))
        if key in seen:copy.append(dict(candidate_id=r['candidate_id'],duplicate_of=seen[key],document_id=d['id']));continue
        seen[key]=r['candidate_id']
        if r['event_role']=='evaluation_reserved':evaluation.append(r)
        elif r['quality_flags']:held.append(r)
        else:clean.append(r)
    clean.sort(key=lambda r:(r['actor_role']=='auxiliary_training_only',r['actor_id'],r['lens_id'],r['event_date'],r['candidate_id']))
    from jsonschema import Draft202012Validator
    dv=Draft202012Validator(json.loads((ROOT/'schemas/acquisition-v1/document.schema.json').read_text()))
    cv=Draft202012Validator(json.loads((ROOT/'schemas/acquisition-v1/candidate.schema.json').read_text()))
    for d in docs:dv.validate(d)
    for r in clean+held+evaluation:cv.validate(r)
    rows=[];suggestions=[];refs={}
    for r in clean:
        label,rationale=suggest(r)
        rid='S-'+r['candidate_id'].split('-')[-1][:12]
        row=dict(queue_version=RULE_VERSION,record_type='annotation_task',row_id=rid,candidate_id=r['candidate_id'],
            selection_kind='targeted_retrieved_candidate',passage_id='passage-'+digest(f"{r['document_id']}:{r['start']}:{r['end']}".encode()),related_candidate_ids='',
            event_id=r['event_id'],document_id=r['document_id'],actor_id=r['actor_id'],actor_role=r['actor_role'],event_date=r['event_date'],lens_id=r['lens_id'],lens_proposition=r['proposition'],
            source_url=r['source_url'],attachment_url='',document_issuer=r['issuer'],speaker=r['speaker'],language=r['language'],language_review_required='false',text_sha256=r['text_sha256'],
            start=str(r['start']),end=str(r['end']),exact_passage=r['exact_passage'],context_start=str(r['start']-len(r['context_before'])),context_end=str(r['end']+len(r['context_after'])),
            context_before=r['context_before'],context_after=r['context_after'],offset_unit='unicode_code_point_half_open',codebook_version='consolidated-v1',translation_aid_id='',
            label='',annotator_id='',review_status='',review_notes='',reading_text=re.sub(r'\s+',' ',r['exact_passage']).strip(),
            source_qualification=r['translation_provenance']+'; '+r['date_basis']+'; targeted acquisition, not representative period sampling.',policy_evidence_form=r['policy_evidence_form'],quality_flags='',quarantine='false',mechanical_resolutions='',event_role='development_only',
            leakage_group_id=r['leakage_group_id'],priority=80 if label=='unresolved' else 30,priority_reasons='conditional_or_polarity_review' if label=='unresolved' else 'unreviewed_direct_evidence',
            existing_annotation_id='',existing_label='',existing_provenance='',existing_review_notes='',ai_suggested_label=label,ai_rationale=rationale,
            ai_review_flags=RULE_VERSION+'; deterministic literal-cue rules authored by assistant; AI-generated/unreviewed, no model inference or probability',human_label='',human_annotator_id='',human_review_notes='',human_independent='false',
            **{field:'' for field in QUALITY_RESPONSE_OPTIONS})
        rows.append(row);suggestions.append(dict(candidate_id=r['candidate_id'],label=label,rationale=rationale,method=RULE_VERSION,origin='ai_generated_unreviewed',human_reviewed=False,training_approved=False))
        refs[r['candidate_id']]=dict(r,source_text_path=str(OUT/bydoc[r['document_id']]['text_path']))
    relatives=defaultdict(list)
    for r in rows:relatives[r['passage_id']].append(r['candidate_id'])
    for r in rows:r['related_candidate_ids']=';'.join(c for c in relatives[r['passage_id']] if c!=r['candidate_id'])
    rows.sort(key=lambda r:(-r['priority'],r['actor_role']=='auxiliary_training_only',r['actor_id'],r['event_date'],r['row_id']))
    PACKET.mkdir(parents=True,exist_ok=True)
    packet=digest(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode())
    previous_manifest=json.loads((PACKET/'manifest.json').read_text()) if (PACKET/'manifest.json').exists() else {}
    created_at=previous_manifest.get('created_at',utcnow()) if previous_manifest.get('packet_id')==packet else utcnow()
    # Never mutate a packet after a real return references it. New acquisitions
    # require a new version rather than silently changing a reviewer's baseline.
    for ledger in (OUT.parent/'workflow-returns').glob('*/ledger.json'):
        if (PACKET/'manifest.json').exists():
            prior=json.loads((PACKET/'manifest.json').read_text())
            if json.loads(ledger.read_text()).get('baseline_sha256')==prior['files']['review_queue.json'] and prior['packet_id']!=packet:
                raise ValueError('Reviewed packet is frozen; increment sprint packet version')
    write_json(PACKET/'review_queue.json',rows);checkpoint_csv(PACKET/'orbit-development-review.csv',rows)
    html_path=PACKET/'orbit-development-review.html'
    # Regeneration is deterministic and permitted only before any return exists.
    if html_path.exists():html_path.unlink()
    render(html_path,rows,packet)
    write_json(PACKET/'progress-backup.json',dict(format='orbit-development-responses-v2',packet_id=packet,saved_at=created_at,provenance='AI-generated unreviewed suggestions; no human decisions',settings={},responses={}))
    write_json(PACKET/'source_refs.json',refs);write_json(PACKET/'ai_suggestions.json',suggestions)
    write_json(PACKET/'manifest.json',dict(version=RULE_VERSION,packet_id=packet,created_at=created_at,records=len(rows),events=sorted({r['event_id'] for r in rows}),new_clean_records=len(rows),mechanically_clean=len(rows),quarantined=0,evaluation_records=0,files={f:digest((PACKET/f).read_bytes()) for f in ('review_queue.json','orbit-development-review.csv','orbit-development-review.html','source_refs.json','ai_suggestions.json','progress-backup.json')}))
    for name,value in [('clean.json',clean),('held.json',held),('evaluation.json',evaluation),('rejected.json',rejected),('source_event_manifest.json',docs),('copy_diagnostics.json',copy)]:write_json(OUT/name,value)
    if held:checkpoint_csv(OUT/'relevant-held.csv',[dict(candidate_id=r['candidate_id'],actor=r['actor_id'],lens=r['lens_id'],date=r['event_date'],source=r['source_url'],reasons=';'.join(r['quality_flags']),start=r['start'],end=r['end'],passage=r['exact_passage']) for r in held])
    report=dict(documents_retrieved=len(docs),new_source_documents=sum(d['new_source_document'] for d in docs),new_distinct_texts=len({d['text_sha256'] for d in docs if d['new_source_document']}),attempted_source_urls=len(s.state['done']),queries=len(s.state['queries']),pending=len(s.state['pending']),batches=s.state['batches'],
        clean_pairs=len(clean),clean_passages=len({r['passage_id'] for r in rows}),clean_events=len({r['event_id'] for r in clean}),clean_independent_groups=len({r['leakage_group_id'] for r in clean}),
        clean_documents=len({r['document_id'] for r in clean}),held_pairs=len(held),new_evaluation_pairs=len(evaluation),rejected_pairs=len(rejected),duplicate_diagnostics=len(copy)+len(json.loads((OUT/'duplicates.json').read_text())),
        clean_by_actor={a:dict(pairs=sum(r['actor_id']==a for r in clean),events=len({r['event_id'] for r in clean if r['actor_id']==a}),groups=len({r['leakage_group_id'] for r in clean if r['actor_id']==a}),lenses=dict(Counter(r['lens_id'] for r in clean if r['actor_id']==a))) for a in ('USA','EU','TUR','IND','ZAF','GBR')},
        clean_by_year=dict(sorted(Counter(r['event_date'][:4] for r in clean).items())),suggested_classes=dict(Counter(r['label'] for r in suggestions)),approved_new_labels=0,existing_eligible_examples=38,existing_eligible_events=8,
        hold_reasons=dict(Counter(f for r in held for f in r['quality_flags'])),selection='targeted_training_acquisition_not_position_estimation',suggestion_method=RULE_VERSION)
    write_json(OUT/'final_yield.json',report)
    write_json(OUT/'yield.json',report)
    write_json(OUT/'last_batch_checkpoint.json',dict(batches=s.state['batches'],pending_urls=[t['url'] for t in s.state['pending']],queries=len(s.state['queries']),yield_counters=report,admission_stage='post_quality_and_connected_split_audit'))
    # Bounded diagnostic controls, separate from the clean stance review and
    # from all historical/new reserved evaluation material. No stance assigned.
    controls=[]
    for d in docs:
        if d['event_role']!='development_only' or not d['new_source_document']:continue
        text=(OUT/d['text_path']).read_text()
        for m in re.finditer(r'[^\n]{80,900}',text):
            if ANCHOR.search(m.group()) and not any(re.search(p,m.group(),re.I) for p in __import__('orbit_data.acquisition_sprint',fromlist=['PATTERNS']).PATTERNS.values()):
                controls.append(dict(candidate_id='control-sprint-'+digest((d['id']+str(m.start())).encode()),document_id=d['id'],event_id=d['event_id'],event_role=d['event_role'],actor_id=d['actor_id'],start=m.start(),end=m.end(),exact_passage=m.group(),source_url=d['canonical_url'],text_sha256=d['text_sha256'],selection_kind='deterministic_hash_sample_nonretrieved',human_label='',ai_suggested_label=''))
    controls=sorted(controls,key=lambda r:digest(('controls-2026:'+r['candidate_id']).encode()))[:12]
    write_json(OUT/'retrieval-controls.json',controls)
    checkpoint_csv(OUT/'coverage.csv',[dict(actor=a,lens=l,year=y,documents=len({r['document_id'] for r in clean if r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==y}),events=len({r['event_id'] for r in clean if r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==y}),pairs=sum(r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==y for r in clean),held_pairs=sum(r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==y for r in held)) for a in ('USA','EU','TUR','IND','ZAF','GBR') for l in ('territorial_recognition','troop_withdrawal','military_assistance','sanctions','invasion_responsibility') for y in map(str,range(2014,2027))])
    print(json.dumps(report,indent=2));return report

if __name__=='__main__': build()
