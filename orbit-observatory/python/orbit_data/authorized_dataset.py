"""Record-scoped grants and documentary source clearances, without rewriting reviews."""
import json
from collections import Counter
from pathlib import Path
from .validation import ROOT,digest,validate_record,load_config
from .reviewed import write_immutable
from .experimental_dataset import counts
from .training import eligible_training_rows

OUTPUT=ROOT.parent/'.local/experimental-baseline-v2'
PRIOR=ROOT.parent/'.local/experimental-baseline-v1'
POLICY=ROOT/'configs/training-v3/pipeline.json'
CLEARANCE=ROOT.parent/'.local/source-clearance-20261024/clearance_decisions.json'


def load_reviews():
    packet=ROOT.parent/'.local/development-review-expanded-v2-20261023'
    if digest((packet/'review_queue.json').read_bytes())!=json.loads((packet/'manifest.json').read_text())['files']['review_queue.json']:raise ValueError('Frozen review packet changed')
    baseline=json.loads((packet/'review_queue.json').read_text())
    row_index={};annotations={};review_hashes={}
    for name in ('Badr_A-development-0001','Badr_A-expanded-0002'):
        folder=ROOT.parent/'.local/workflow-returns'/name
        ledger=json.loads((folder/'ledger.json').read_text())
        if digest((folder/'submitted.csv').read_bytes())!=ledger['submission_sha256']:raise ValueError('Prior CSV changed')
        review_hashes[name]=digest((folder/'annotations.json').read_bytes())
        canonical=json.loads((folder/'annotations.json').read_text())
        if [a['id'] for a in canonical]!=ledger['annotation_ids']:raise ValueError('Canonical annotation IDs changed')
        import csv
        with (folder/'submitted.csv').open(encoding='utf-8-sig',newline='') as stream:submitted=list(csv.DictReader(stream))
        stored=json.loads((folder/'returned_rows.json').read_text())
        if stored!=submitted:raise ValueError('Stored return differs from exact submitted CSV')
        for a in canonical:
            validate_record(a);annotations[a['claim_id']]=a
        for row in json.loads((folder/'returned_rows.json').read_text()):
            if row['human_label']:row_index[row['candidate_id']]=row
    if len(baseline)!=113 or set(annotations)!={r['candidate_id'] for r in baseline} or set(row_index)!=set(annotations):raise ValueError('113-record reviewed set does not match')
    for source in baseline:
        row=row_index[source['candidate_id']];a=annotations[source['candidate_id']]
        if a['label']!=row['human_label'] or a['annotator_id']!=row['human_annotator_id'] or a['review_notes']!=row['human_review_notes']:raise ValueError('Annotation changed from submitted judgment')
        for key in ('candidate_id','event_id','document_id','exact_passage','text_sha256','start','end','lens_proposition'):
            if str(row[key])!=str(source[key]):raise ValueError('Review evidence mismatch: '+key)
    return baseline,row_index,annotations,review_hashes


def authorization(baseline,annotations,review_hashes):
    entries=[]
    for row in baseline:
        a=annotations[row['candidate_id']]
        entries.append(dict(candidate_id=row['candidate_id'],annotation_id=a['id'],annotator_id=a['annotator_id'],origin=a['origin'],
            reviewed_label=a['label'],supervised_training_approved=a['label'] in ('support','oppose','no_stance','mixed'),
            existing_human_independent_check=a.get('human_independent_check'),blind_independent_annotation=False))
    grant=dict(record_type='training_authorization',version='1.0.0',id='Badr_A-experimental-grant-20261024',authorized_by='Badr_A',authorization_date='2026-10-24',
        authority='Explicit user request extends experimental training use to the 68 earlier development reviews and 45 newly approved reviews.',
        policy_version='experimental-training-3.0.0',new_human_or_blind_checks_asserted=False,source_holds_cleared=False,unresolved_targets_approved=False,
        review_annotation_hashes=review_hashes,records=entries)
    write_immutable(OUTPUT/'training_authorization.json',grant)
    write_immutable(ROOT/'annotations/authorizations/20261024-all113.json',grant)
    return grant


def validate_clearances(decisions,baseline):
    index={r['candidate_id']:r for r in baseline}
    seen=set()
    for decision in decisions:
        if decision['id'] in seen:raise ValueError('Duplicate clearance ID')
        seen.add(decision['id'])
        source=index[decision['candidate_id']]
        if not set(decision['cleared_flags'])<=set(source['quality_flags'].split(';')):raise ValueError('Clearance removes an absent flag')
        if decision.get('label_changed') is not False or decision.get('independent_human') is not False:raise ValueError('Source check cannot create a new label/independent human judgment')
        if decision['source_text_sha256']!=source['text_sha256']:raise ValueError('Clearance refers to another text')
        if not decision.get('criterion_satisfied') or not decision.get('evidence'):raise ValueError('Clearance needs documentary evidence')
        for evidence in decision['evidence']:
            path=(ROOT.parent/evidence['path']).resolve()
            if not path.is_relative_to(ROOT.parent.resolve()) or digest(path.read_bytes())!=evidence['sha256']:raise ValueError('Clearance evidence path/hash mismatch')
            if 'exact_text' in evidence:
                if path.read_text()[evidence['start']:evidence['end']]!=evidence['exact_text']:raise ValueError('Clearance quotation offsets mismatch')


def assess(source,row,annotation,group,split,decisions,apply_clearances):
    flags=set(filter(None,source['quality_flags'].split(';')));checks={
        'source_eligibility':row['human_source_eligibility']=='eligible',
        'text_quality':row['human_text_quality']=='usable',
        'attribution':row['human_attribution']=='attributable'}
    applied=[]
    if apply_clearances:
        for d in decisions:
            if d['candidate_id']!=source['candidate_id']:continue
            flags-=set(d['cleared_flags'])
            for field in d['cleared_checks']:
                # Missing/defective evidence cannot be waived by a source-policy decision.
                if field=='text_quality' and row['human_text_quality']=='defective':raise ValueError('Defective text needs a revision, not a waiver')
                checks[field]=True
            applied.append(d['id'])
    reasons=[]
    if source['event_id'] in split['excluded_from_training_and_tuning_event_ids'] or group in split['reserved_leakage_group_ids']:reasons.append('reserved_event_or_related_group')
    scope_flags={f for f in flags if 'scope' in f or 'W1' in f};source_flags=flags-scope_flags
    if source_flags:reasons.append('source_holds_remain');reasons.extend('hold:'+f for f in sorted(source_flags))
    for field,cleared in checks.items():
        if not cleared:reasons.append(field+'_not_cleared')
    label=annotation['label']
    if label not in ('support','oppose','no_stance','mixed'):reasons.append('excluded_supervised_target:'+label)
    if scope_flags:reasons.extend('preserved:'+f for f in sorted(scope_flags))
    expected='no_relevant_stance' if label=='no_stance' else 'exact_target_met'
    if row['human_scope']!=expected:reasons.append('strict_scope_not_met')
    return reasons,sorted(flags),checks,applied


def validate_view(row):
    from jsonschema import Draft202012Validator
    Draft202012Validator(json.loads((ROOT/'schemas/experimental-v2/training_view.schema.json').read_text())).validate(row)
    if row['record_type']!='experimental_training_example' or row['schema_version']!='2.0.0':raise ValueError('Wrong training-view contract')
    validate_record(row['human_annotation'])
    a=row['human_annotation']
    for field in ('label','origin','ai_assisted','independent_human','review_status'):
        if row[field]!=a[field]:raise ValueError('Training view altered annotation provenance')
    if row['human_independent_check']!=a.get('human_independent_check'):raise ValueError('A grant cannot assert a human check')
    if row['candidate_id']!=a['claim_id'] or row['annotation_id']!=a['id']:raise ValueError('Annotation reference mismatch')
    if row['end']-row['start']!=len(row['passage']):raise ValueError('Training offsets mismatch')
    if row['proposition']!=load_config()[1][row['lens_id']]['definition']:raise ValueError('Changed proposition')
    if row['label'] not in ('support','oppose','no_stance','mixed') or row['alignment_score'] is not None:raise ValueError('Abstention/alignment cannot enter targets')
    if not all(row[k] is True for k in ('training_approved','record_scoped_authorization_verified','source_eligibility_cleared','text_quality_cleared','scope_cleared')):raise ValueError('Training gates not met')


def build():
    previous=json.loads((PRIOR/'dataset_manifest.json').read_text())
    for name,sha in previous['files'].items():
        if digest((PRIOR/name).read_bytes())!=sha:raise ValueError('Previous frozen dataset changed')
    baseline,rows,anns,review_hashes=load_reviews();grant=authorization(baseline,anns,review_hashes)
    decisions=json.loads(CLEARANCE.read_text());validate_clearances(decisions,baseline)
    groups=json.loads((PRIOR/'leakage_groups.json').read_text());split=json.loads((PRIOR/'training_split.json').read_text())
    frozen=[];ledgers=[];backend=[];before=[];after_grant=[]
    corpus=ROOT.parent/'.local/expansion-v6'
    pilot=ROOT.parent/'.local/pilot-v1'
    documents={d['id']:(d,pilot) for d in json.loads((pilot/'records.json').read_text()) if d['record_type']=='document'}
    documents.update({d['document_id']:(d,corpus) for d in json.loads((corpus/'cleared_catalog.json').read_text())})
    for source in baseline:
        cid=source['candidate_id'];row=rows[cid];a=anns[cid]
        doc,cache=documents[source['document_id']];stored=(cache/doc['text_path']).read_bytes()
        if digest(stored)!=source['text_sha256'] or stored.decode()[int(source['start']):int(source['end'])]!=source['exact_passage']:raise ValueError('Cached source offsets/hash changed')
        group=groups['event_groups'][source['event_id']]
        old_reasons,_,_,_=assess(source,row,a,group,split,decisions,False)
        if not old_reasons:after_grant.append(dict(candidate_id=cid,lens_id=source['lens_id'],event_id=source['event_id'],leakage_group_id=group,label=a['label']))
        reasons,flags,checks,applied=assess(source,row,a,group,split,decisions,True)
        ledgers.append(dict(candidate_id=cid,annotation_id=a['id'],actor_id=source['actor_id'],lens_id=source['lens_id'],event_id=source['event_id'],
            label=a['label'],training_authorized=a['label'] not in ('unresolved','not_applicable'),included=not reasons,reasons=reasons,
            original_flags=source['quality_flags'],effective_flags=flags,clearance_ids=applied,human_independent_check=a.get('human_independent_check'),blind_independent_annotation=False))
        evidence=dict(candidate_id=cid,event_id=source['event_id'],document_id=source['document_id'],actor_id=source['actor_id'],actor_role=source['actor_role'],
            event_date=source['event_date'],lens_id=source['lens_id'],proposition=source['lens_proposition'],source_url=source['source_url'],issuer=source['document_issuer'],language=source['language'],
            text_sha256=source['text_sha256'],start=int(source['start']),end=int(source['end']),exact_passage=source['exact_passage'],reading_text=source['reading_text'],
            context_before=source['context_before'],context_after=source['context_after'],quality_flags=';'.join(flags),original_quality_flags=source['quality_flags'],clearance_ids=applied,
            quarantine=bool(flags),human_annotation=a,training_authorization_id=grant['id'],training_included=not reasons,exclusion_reasons=reasons,alignment_score=None)
        if group not in split['reserved_leakage_group_ids']:backend.append(evidence)
        if reasons:continue
        frozen.append(dict(record_type='experimental_training_example',schema_version='2.0.0',annotation_id=a['id'],human_annotation=a,candidate_id=cid,
            event_id=source['event_id'],document_id=source['document_id'],actor_id=source['actor_id'],actor_role=source['actor_role'],lens_id=source['lens_id'],event_date=source['event_date'],
            language=source['language'],proposition=source['lens_proposition'],passage=source['exact_passage'],reading_text=source['reading_text'],text_sha256=source['text_sha256'],
            start=int(source['start']),end=int(source['end']),source_url=source['source_url'],leakage_group_id=group,label=a['label'],origin=a['origin'],ai_assisted=a['ai_assisted'],
            review_status=a['review_status'],independent_human=a['independent_human'],human_independent_check=a.get('human_independent_check'),blind_independent_annotation=False,
            training_approved=True,training_approval_id=grant['id'],training_policy_version='experimental-training-3.0.0',record_scoped_authorization_verified=True,
            source_eligibility_cleared=True,text_quality_cleared=True,scope_cleared=True,alignment_score=None,clearance_ids=applied))
    for row in frozen:validate_view(row)
    accepted,rejected=eligible_training_rows(frozen,split)
    if rejected or len(accepted)!=len(frozen):raise ValueError('Policy and freeze disagree')
    prior_counts=json.loads((PRIOR/'counts.json').read_text())['eligible']
    summary=dict(reviewed_records=113,legacy_records=68,expanded_records=45,conditional_authorizations=113,
        resolved_targets_authorized=sum(a['label'] not in ('unresolved','not_applicable') for a in anns.values()),
        before_current_task=prior_counts,after_authorization_before_clearance=counts(after_grant),after_clearance=counts(frozen),
        original_label_counts=dict(Counter(a['label'] for a in anns.values())),eligible_label_counts=dict(Counter(r['label'] for r in frozen)),
        included_legacy=sum(r['candidate_id'] in {x['candidate_id'] for x in json.loads((ROOT.parent/'.local/workflow-returns/Badr_A-development-0001/returned_rows.json').read_text())} for r in frozen),
        primary_exclusions=dict(Counter(x['reasons'][0] for x in ledgers if x['reasons'])),remaining_flags=dict(Counter(f for x in ledgers for f in x['effective_flags'])),
        clearance_decisions=len(decisions),no_new_human_checks_asserted=True,public_scores_changed=False)
    payloads={'dataset.json':frozen,'inclusion_exclusion_ledger.json':ledgers,'clearances.json':decisions,'counts.json':summary,'leakage_groups.json':groups,'training_split.json':split,
        'backend_evidence.json':backend,'preprocessing.json':dict(json.loads((PRIOR/'preprocessing.json').read_text()),policy_version='experimental-training-3.0.0')}
    for name,obj in payloads.items():write_immutable(OUTPUT/name,obj)
    manifest=dict(version='experimental-dataset-2.0.0',policy_version='experimental-training-3.0.0',policy_sha256=digest(POLICY.read_bytes()),
        authorization_sha256=digest((OUTPUT/'training_authorization.json').read_bytes()),review_annotation_hashes=review_hashes,
        files={name:digest((OUTPUT/name).read_bytes()) for name in list(payloads)+['training_authorization.json']},
        prior_dataset_manifest_sha256=digest((PRIOR/'dataset_manifest.json').read_bytes()),grouping_changed=False,evaluation_untouched=True,
        human_check_provenance='Preserved from canonical annotations; the new grant asserts no additional checks',W1_preserved=True)
    write_immutable(OUTPUT/'dataset_manifest.json',manifest)
    print(json.dumps(summary,indent=2));return manifest

if __name__=='__main__':build()
