"""Reproducible metadata, coverage and held-evidence checkpoint; no fitting."""
import json,re
from collections import Counter
from pathlib import Path
from .focal_retrieval import OUT,OLD
from .focal_review import LENSES,write_table,windows
from .component_review import PACKET as COMPONENTS,SCOPE_HOLDS
from .validation import ROOT,digest
from .collect import write_json
from .acquisition_sprint import ANCHOR,PATTERNS

def build():
    read=lambda p:json.loads(p.read_text())
    state=read(OUT/'state.json');before=read(OLD/'clean.json');clean=read(OUT/'clean.json');held=read(OUT/'held.json');docs=read(OUT/'source_event_manifest.json')
    components=list(read(COMPONENTS/'source_refs.json').values());component_originals={r['derived_from_candidate_id'] for r in components}
    reclassified=[dict(component_candidate_id=r['candidate_id'],derived_from_candidate_id=r['derived_from_candidate_id'],original_candidate_id=r.get('recovery_of') or r['derived_from_candidate_id'],event_id=r['event_id'],source_url=r['source_url'],text_sha256=r['text_sha256'],start=r['start'],end=r['end'],retained_full_target_holds=';'.join(r['target_scope_flags']),strict_label_changed=False,annotation_transferred=False,training_approved=False) for r in components if r['acquisition_kind']=='recovered_held']
    write_json(OUT/'component_reclassification_ledger.json',reclassified);write_table(OUT/'component_reclassification_ledger.csv',reclassified)
    ledger=read(OUT/'clearance_ledger.json')+read(OUT/'joint_clearance_ledger.json')
    write_json(OUT/'held_clearance_ledger.json',ledger)
    flat=[]
    for r in ledger:
        for p in r['clearances']:flat.append(dict(original_candidate_id=r['original_candidate_id'],replacement_candidate_id=r.get('replacement_candidate_id'),previous_hold=p['previous_hold'],criterion=p['criterion'],source_url=p['source_url'],source_text_sha256=p['source_text_sha256'],proof_start=p['proof_start'],proof_end=p['proof_end'],proof_text=p['proof_text'],method=p['method'],remaining_holds=';'.join(r['remaining_holds']),annotation_transferred=False,training_approved=False))
    write_table(OUT/'held_clearance_ledger.csv',flat)
    disposition=[]
    for r in held:
        category='component_evidence_full_target_scope_held' if r['candidate_id'] in component_originals else 'technical_source_or_attribution_hold'
        if set(r['quality_flags'])<={'legal_implementation_only','described_third_party_assistance_no_own_direction'}:category='policy_component_or_own_direction_not_established'
        disposition.append(dict(candidate_id=r['candidate_id'],actor_id=r['actor_id'],lens_id=r['lens_id'],category=category,holds=';'.join(r['quality_flags']),event_id=r['event_id'],source_url=r['source_url']))
    write_table(OUT/'held_dispositions.csv',disposition);write_json(OUT/'held_dispositions.json',disposition)
    write_json(OUT/'remaining_source_holds.json',[r for r in held if r['candidate_id'] not in component_originals])
    # Retain old partial-scope auxiliary evidence without reopening bulk UK review.
    oldheld=read(OLD/'held.json')
    retained_aux=[dict(candidate_id=r['candidate_id'],actor_id=r['actor_id'],lens_id=r['lens_id'],event_id=r['event_id'],source_url=r['source_url'],holds=r['quality_flags'],disposition='Previously retained component/source evidence; no new AI label or annotation request in this focal increment') for r in oldheld if r['actor_id']=='GBR']
    write_json(OUT/'previous_auxiliary_retention_index.json',retained_aux)
    coverage=[]
    for a in ['USA','EU','TUR','IND','ZAF']:
        for l in LENSES:
            old=[r for r in before if r['actor_id']==a and r['lens_id']==l];new=[r for r in clean if r['actor_id']==a and r['lens_id']==l];comp=[r for r in components if r['actor_id']==a and r['lens_id']==l]
            coverage.append(dict(actor=a,lens=l,before_strict_pairs=len(old),before_events=len({r['event_id'] for r in old}),before_groups=len({r['leakage_group_id'] for r in old}),strict_newly_collected=sum(r['acquisition_kind']=='newly_collected' for r in new),strict_recovered=sum(r['acquisition_kind']=='recovered_held' for r in new),after_strict_pairs=len(old+new),after_strict_events=len({r['event_id'] for r in old+new}),after_strict_groups=len({r['leakage_group_id'] for r in old+new}),component_pairs=len(comp),component_newly_collected=sum(r['acquisition_kind']=='newly_collected' for r in comp),component_previously_held=sum(r['acquisition_kind']=='recovered_held' for r in comp),component_events=len({r['event_id'] for r in comp}),component_groups=len({r['leakage_group_id'] for r in comp}),remaining_noncomponent_held=sum(r['actor_id']==a and r['lens_id']==l and r['candidate_id'] not in component_originals for r in held)))
    write_table(OUT/'actor_lens_before_after.csv',coverage);write_json(OUT/'actor_lens_before_after.json',coverage)
    years=[]
    for a in ['USA','EU','TUR','IND','ZAF']:
        for y in range(2014,2027):
            for l in LENSES:
                rs=[r for r in clean if r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==str(y)];cs=[r for r in components if r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==str(y)]
                ds=[d for d in docs if d['actor_id']==a and d['event_date'][:4]==str(y)]
                years.append(dict(actor=a,lens=l,year=y,inventory_documents_actor_year=len(ds),strict_documents=len({r['document_id'] for r in rs}),strict_pairs=len(rs),strict_events=len({r['event_id'] for r in rs}),strict_groups=len({r['leakage_group_id'] for r in rs}),component_documents=len({r['document_id'] for r in cs}),component_pairs=len(cs),component_events=len({r['event_id'] for r in cs}),component_groups=len({r['leakage_group_id'] for r in cs}),held_pairs=sum(r['actor_id']==a and r['lens_id']==l and r['event_date'][:4]==str(y) for r in held)))
    write_table(OUT/'actor_lens_year.csv',years)
    # Bounded source-only controls; these are not new stance suggestions.
    controls=[]
    for d in docs:
        if d['event_role']!='development_only':continue
        text=(OUT/d['text_path']).read_text()
        for a,b in windows(text,d['body_start']):
            p=text[a:b]
            if len(p)>900 or not ANCHOR.search(p) or any(re.search(v,p,re.I) for v in PATTERNS.values()):continue
            controls.append(dict(candidate_id='control-focus2-'+digest((d['id']+':'+str(a)).encode()),document_id=d['id'],event_id=d['event_id'],event_role='development_only',leakage_group_id=d['leakage_group_id'],actor_id=d['actor_id'],source_url=d['canonical_url'],text_sha256=d['text_sha256'],start=a,end=b,exact_passage=p,context_before=text[max(0,a-500):a],context_after=text[b:b+500],human_label='',ai_suggested_label='',selection_kind='deterministic_hash_sample_nonretrieved_diagnostic_not_main_review'))
    controls=sorted(controls,key=lambda r:digest(('focal-controls-2026:'+r['candidate_id']).encode()))[:12]
    write_json(OUT/'retrieval_controls.json',controls);write_table(OUT/'retrieval_controls.csv',controls)
    baseline=read(ROOT.parent/'.local/experimental-baseline-v2/dataset.json')
    if isinstance(baseline,dict):baseline=baseline.get('rows',baseline.get('examples',baseline.get('records')))
    assert isinstance(baseline,list)
    outcome=Counter(v['status'] for v in state['done'].values());unresolved=Counter(f for r in held if r['candidate_id'] not in component_originals for f in r['quality_flags'])
    allnew=clean+components;newly=[r for r in allnew if r['acquisition_kind']=='newly_collected']
    report=dict(version='focal-acquisition-report-2.1.0',collection_cutoff='2026-10-24',final_validation_date='2026-10-25',batches=state['batches'],queries_attempted=len(state['queries']),source_urls_attempted=len(state['done']),source_url_outcomes=dict(outcome),stored_documents=len(docs),development_documents=sum(d['event_role']=='development_only' for d in docs),reserved_documents=sum(d['event_role']=='evaluation_reserved' for d in docs),strict=read(OUT/'yield.json'),components=read(OUT/'component_yield.json'),combined=dict(pairs=len(allnew),passages=len({(r['document_id'],r['start'],r['end']) for r in allnew}),events=len({r['event_id'] for r in allnew}),groups=len({r['leakage_group_id'] for r in allnew}),newly_collected_pairs=len(newly),newly_collected_events=len({r['event_id'] for r in newly}),newly_collected_groups=len({r['leakage_group_id'] for r in newly}),new_event_families=len({r['event_id'] for r in newly if not r.get('known_event_family')})),held_dispositions=dict(Counter(r['category'] for r in disposition)),remaining_overlapping_holds=dict(unresolved),old_held_audited=len(oldheld),clearance_actions=len(flat),clearance_ledger_records=len(ledger),controls=len(controls),approved_dataset=dict(examples=len(baseline),events=len({r['event_id'] for r in baseline}),classes=dict(Counter(r['label'] for r in baseline))),new_approved_labels=0,models_rerun=False,pending_urls=len(state['pending_urls']),pending_queries=len(state['pending_queries']),deferred_queries=len(state.get('deferred_queries',[])),main_bottleneck='Exact-target scope/policy relevance and attribution; title-only discovery was improved by MEA full-text search. Remaining access gaps are host-specific.',resume_command='PYTHONPATH=python python -m orbit_data.focal_collection --batches 50 --batch-size 20 --queries-per-batch 8 --finalize')
    report['combined']['genuinely_new_groups']=len({r['leakage_group_id'] for r in newly if not r.get('known_event_family')})
    outcomes=[]
    for u,v in state['done'].items():
        reason=v.get('reason','');stage='stored_date_verified_pending_passage_admission'
        if v['status']!='collected':
            stage='network_access'
            if 'No Russia-Ukraine' in reason:stage='conflict_filter'
            elif 'Missing/out-of-period' in reason:stage='document_identity_date_or_period'
            elif 'Not adopted' in reason:stage='institutional_source_clearance'
            elif '404' in reason:stage='discovery_missing_document'
            elif 'Maintenance/navigation' in reason:stage='text_or_document_identity'
        outcomes.append(dict(url=u,status=v['status'],stage=stage,document_id=v.get('document_id',''),reason=reason))
    report['source_outcome_stages']=dict(Counter(r['stage'] for r in outcomes))
    write_json(OUT/'acquisition_report.json',report)
    write_table(OUT/'source_outcomes.csv',outcomes)
    write_json(OUT/'last_batch_checkpoint.json',dict(version=report['version'],batches=state['batches'],queries=state['queries'],query_definitions=state.get('query_definitions',{}),pending_urls=state['pending_urls'],pending_queries=state['pending_queries'],deferred_queries=state.get('deferred_queries',[]),report=report))
    print(json.dumps({k:report[k] for k in ['source_urls_attempted','stored_documents','combined','approved_dataset','held_dispositions']},indent=2));return report

if __name__=='__main__':build()
