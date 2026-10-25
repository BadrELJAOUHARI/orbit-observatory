"""Import one returned consolidated/blind CSV, preserving all prior judgments."""
import argparse
import csv
import io
import json
import re
from .validation import ROOT,digest,validate_dataset
from .workflow import load_corpus,csv_cell,QUALITY_RESPONSE_OPTIONS
from .collect import utcnow
from .reviewed import write_immutable

HUMAN={'human_label','human_annotator_id','human_review_notes','human_independent'}|set(QUALITY_RESPONSE_OPTIONS)


def audit_return(rows,baseline,blind=False):
    """Report all structural/evidence conflicts and prior-label differences together."""
    from collections import Counter
    expected={r['candidate_id']:r for r in baseline}
    counts=Counter(r.get('candidate_id') for r in rows)
    errors=[];differences=[]
    for identifier,count in counts.items():
        if identifier not in expected:errors.append(dict(candidate_id=identifier,reason='unknown_candidate'))
        if count!=1:errors.append(dict(candidate_id=identifier,reason='duplicate_candidate',count=count))
    for identifier in set(expected)-set(counts):errors.append(dict(candidate_id=identifier,reason='missing_candidate'))
    for row in rows:
        original=expected.get(row.get('candidate_id'))
        if original is None:continue
        changed=[k for k in set(original)-HUMAN if row.get(k)!=csv_cell(original[k])]
        if changed:errors.append(dict(candidate_id=row['candidate_id'],reason='immutable_fields_changed',fields=sorted(changed)))
        try:validate_return([row],[original],blind)
        except (ValueError,KeyError) as error:errors.append(dict(candidate_id=row['candidate_id'],reason='row_validation',detail=str(error)))
        if original.get('existing_label') and row.get('human_label') and original['existing_label']!=row['human_label']:
            differences.append(dict(candidate_id=row['candidate_id'],row_id=row['row_id'],
                previous_annotation_id=original['existing_annotation_id'],previous_label=original['existing_label'],submitted_label=row['human_label'],
                handling='Append new reviewed judgment; preserve previous annotation, revision lineage and all source/scope holds.'))
    return dict(expected_records=len(baseline),returned_records=len(rows),fatal_conflicts=errors,prior_label_differences=differences,
        independence_counts=dict(Counter(r.get('human_independent') for r in rows)),
        policy='Reported extra checks do not change record independence without explicit record-level, no-suggestion-exposure provenance.')


def validate_return(rows,baseline,blind=False):
    expected={r['candidate_id']:r for r in baseline}
    if len(rows)!=len(expected) or len({r['candidate_id'] for r in rows})!=len(rows):
        raise ValueError('Returned CSV dropped or duplicated rows')
    reviewed=[]
    for row in rows:
        original=expected[row['candidate_id']]
        if set(row)!=set(original):raise ValueError('Returned columns differ')
        if any(row[k]!=csv_cell(original[k]) for k in set(original)-HUMAN):
            raise ValueError('Read-only source, suggestion, history or flags were edited')
        if row['human_independent'] not in ('','false','true'):raise ValueError('Independence must be explicit true/false')
        for field,values in QUALITY_RESPONSE_OPTIONS.items():
            if row.get(field,'') not in ('',)+values:raise ValueError('Invalid separate quality response')
        has_quality=any(row.get(field) for field in QUALITY_RESPONSE_OPTIONS)
        if row['human_label'] or has_quality:
            if row['human_label'] and row['human_label'] not in ('support','oppose','no_stance','mixed','unresolved','not_applicable'):
                raise ValueError('Invalid human label')
            if not row['human_annotator_id'].strip() or not row['human_review_notes'].strip():
                raise ValueError('Reviewed labels need an annotator ID and brief reasoning')
            if not blind and (row['human_independent']=='true' or original.get('event_role')=='evaluation_rehearsal'):
                raise ValueError('Consolidated review cannot create independent judgments or label reserved events')
            if blind and row['human_independent']!='true':
                raise ValueError('Blind independence requires explicit no-prior-exposure confirmation; otherwise record an assisted review separately')
            reviewed.append(row)
    return reviewed


def validate_approval(approval,reviewed,baseline):
    """User-supplied record-scoped approval, distinct from blind independence."""
    expected={r['candidate_id'] for r in reviewed if r.get('human_label')}
    identifiers=approval.get('candidate_ids',[])
    errors=[];index={r['candidate_id']:r for r in baseline}
    if len(identifiers)!=len(set(identifiers)) or set(identifiers)!=expected:errors.append('Approval IDs must exactly match new labeled responses, without duplicates')
    for field,value in [('human_independent_check',True),('training_approved',True),('ai_assisted_initial_annotation',True),('blind_independent_annotation',False)]:
        if approval.get(field) is not value:errors.append('Incorrect approval field: '+field)
    for row in reviewed:
        if row['human_annotator_id']!=approval.get('reviewer_id'):errors.append('Reviewer mismatch: '+row['candidate_id'])
        if index[row['candidate_id']].get('existing_annotation_id'):errors.append('Approval must not reimport previous reviewed rows: '+row['candidate_id'])
        if row['human_independent']!='false':errors.append('Blind flag must remain false: '+row['candidate_id'])
    if errors:raise ValueError(json.dumps(dict(approval_conflicts=errors)))
    return dict(approval,policy_version='experimental-training-2.0.0',source_holds_cleared=False,approval_is_not_eligibility=True)


def select_baseline(rows,blind=False):
    """Recognize the new development-only packet while accepting old returns."""
    output=ROOT.parent/'.local/workflow-v1'
    if not blind:
        for name in ('development-components-focal-v2','development-review-focal-v2','development-review-sprint-v1','development-review-expanded-v2-20261023','development-review-v2'):
            development=ROOT.parent/'.local'/name
            if not (development/'manifest.json').exists():continue
            manifest=json.loads((development/'manifest.json').read_text())
            path=development/'review_queue.json'
            if digest(path.read_bytes())!=manifest['files']['review_queue.json']:
                raise ValueError('Development baseline was modified')
            baseline=json.loads(path.read_text())
            if {r.get('candidate_id') for r in rows}=={r['candidate_id'] for r in baseline}:
                if any(r['event_role']!='development_only' for r in baseline):
                    raise ValueError('Development baseline contains a reserved event')
                return path,baseline
    path=output/('blind_evaluation.json' if blind else 'review_queue.json')
    return path,json.loads(path.read_text())


def import_return(path,review_id,blind=False,approval_json=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',review_id):raise ValueError('Unsafe review ID')
    output=ROOT.parent/'.local/workflow-v1'
    with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    baseline_path,baseline=select_baseline(rows,blind)
    if baseline_path.parent.name=='development-components-focal-v2':
        if blind or approval_json:raise ValueError('Experimental component review cannot grant blind status or strict-target training approval')
        from .component_review import import_component_return
        return import_component_return(path,review_id)
    audit=audit_return(rows,baseline,blind)
    if audit['fatal_conflicts']:raise ValueError(json.dumps(audit,ensure_ascii=False))
    reviewed=validate_return(rows,baseline,blind)
    approval=validate_approval(json.loads(approval_json.read_text()),reviewed,baseline) if approval_json else None
    if approval and blind:raise ValueError('Assisted training approval cannot create blind annotations')
    records,*_=load_corpus();index={r['id']:r for r in records}
    expansion_claims={};sprint_claims={}
    for packet_name in ('development-review-sprint-v1','development-review-focal-v2'):
        sprint=ROOT.parent/'.local'/packet_name
        if not (sprint/'manifest.json').exists():continue
        manifest=json.loads((sprint/'manifest.json').read_text())
        refs_path=sprint/'source_refs.json'
        if digest(refs_path.read_bytes())!=manifest['files']['source_refs.json']:raise ValueError('Sprint references changed')
        new_refs=json.loads(refs_path.read_text())
        if set(new_refs)&set(sprint_claims):raise ValueError('Conflicting candidate IDs across frozen review packets')
        for identifier,ref in new_refs.items():
            if ref['event_role']!='development_only' or ref['quality_flags'] or ref['candidate_id']!=identifier:
                raise ValueError('Sprint source/partition gate failed: '+identifier)
            text=__import__('pathlib').Path(ref['source_text_path']).read_text()
            if (digest(text.encode())!=ref['text_sha256'] or text[ref['start']:ref['end']]!=ref['exact_passage']):
                raise ValueError('Sprint source/evidence gate failed: '+identifier)
        sprint_claims.update(new_refs);index.update(new_refs)
    expansion=ROOT.parent/'.local/expansion-v6'
    if (expansion/'candidates.json').exists():
        from .expansion import validate_expansion,event_roles
        docs=json.loads((expansion/'cleared_catalog.json').read_text());claims=json.loads((expansion/'candidates.json').read_text())
        validate_expansion(docs,claims,event_roles())
        expansion_claims={c['id']:c for c in claims};index.update(expansion_claims)
    def validate_annotations(annotations):
        from .validation import validate_record
        original=[a for a in annotations if a['claim_id'] not in expansion_claims and a['claim_id'] not in sprint_claims]
        validate_dataset(records+original,ROOT.parent/'.local/pilot-v1')
        for a in annotations:
            if a['claim_id'] in sprint_claims:validate_record(a)
            if a['claim_id'] in expansion_claims:
                validate_record(a)
                if expansion_claims[a['claim_id']]['event_id'] in {e for e,r in event_roles().items() if r=='evaluation_reserved'}:
                    raise ValueError('Reserved expansion event cannot receive development annotations')
    previous=[]
    for file in sorted((ROOT.parent/'.local/workflow-returns').glob('*/annotations.json')):
        if file.parent.name!=review_id:previous.extend(json.loads(file.read_text()))
    now=utcnow();annotations=[];quality_responses=[]
    for row in reviewed:
        if blind:
            exposed={a['annotator_id'] for a in records+previous if a['record_type']=='annotation'
                     and a.get('origin')=='ai_assisted_reviewed'
                     and index[a['claim_id']]['event_id']==index[row['candidate_id']]['event_id']}
            if row['human_annotator_id'] in exposed:
                raise ValueError('Annotator has recorded assisted exposure to this event; do not call the new judgment independent')
        if any(row.get(field) for field in QUALITY_RESPONSE_OPTIONS):
            quality_responses.append(dict(candidate_id=row['candidate_id'],annotator_id=row['human_annotator_id'],
                review_id=review_id,review_notes=row['human_review_notes'],independent_human=blind,
                decisions={field:row[field] for field in QUALITY_RESPONSE_OPTIONS},
                disposition='Append-only quality decision; original flags preserved. Not a training/publication approval.'))
        if not row['human_label']:continue
        priors=[a for a in records+previous if a['record_type']=='annotation' and a['claim_id']==row['candidate_id']
                and a['annotator_id']==row['human_annotator_id']]
        common=dict(record_type='annotation',id='annotation-'+digest(f"{review_id}:{row['candidate_id']}:{digest(path.read_bytes())}".encode()),
            claim_id=row['candidate_id'],annotator_id=row['human_annotator_id'],codebook_version='consolidated-v1',label=row['human_label'],
            created_at=now,rationale=row['human_review_notes'],supersedes=priors[-1]['id'] if priors else None)
        if blind:
            common.update(schema_version='1.1.0',origin='human',review_status='independent')
        else:
            common.update(schema_version='1.2.0',origin='ai_assisted_reviewed',batch_id=row['row_id'],review_status='reviewed_non_independent',
                review_notes=row['human_review_notes'],review_provenance='Returned consolidated CSV reviewed by named annotator; AI suggestions visible; non-independent.',
                ai_assisted=True,independent_human=False,scoring_status='not_scored_pending_quality_review')
        if approval:
            common.update(schema_version='1.3.0',human_independent_check=True,training_approved=True,blind_independent_annotation=False,
                training_approval_id='approval-'+digest(approval_json.read_bytes()),training_policy_version='experimental-training-2.0.0',
                review_provenance='Badr_A explicitly confirms human checking of AI-assisted development judgments and approves experimental training. Initial AI assistance retained. Not blind independent annotation.')
        annotations.append(common)
    folder=ROOT.parent/'.local/workflow-returns'/review_id
    if (folder/'ledger.json').exists():
        ledger=json.loads((folder/'ledger.json').read_text())
        if ledger['submission_sha256']!=digest(path.read_bytes()):raise ValueError('Cannot replace a prior reviewed return')
        if ledger.get('approval_sha256')!=(digest(approval_json.read_bytes()) if approval_json else None):raise ValueError('Cannot replace prior training approval')
        validate_annotations(previous+json.loads((folder/'annotations.json').read_text()))
        return ledger
    validate_annotations(previous+annotations)
    if approval:
        write_immutable(folder/'human_check_and_training_approval.json',approval)
        write_immutable(folder/'training_approval_submission.json',json.loads(approval_json.read_text()))
    write_immutable(folder/'annotations.json',annotations)
    write_immutable(folder/'quality_responses.json',quality_responses)
    write_immutable(folder/'returned_rows.json',rows)
    if any(row['candidate_id'] in sprint_claims for row in reviewed):
        write_immutable(folder/'source_references.json',{row['candidate_id']:sprint_claims[row['candidate_id']] for row in reviewed if row['candidate_id'] in sprint_claims})
    for filename,data in [('submitted.csv',path.read_bytes())]+([('submitted_approval.json',approval_json.read_bytes())] if approval else []):
        target=folder/filename
        if target.exists():
            if target.read_bytes()!=data:raise ValueError('Cannot replace original submission bytes')
        else:target.write_bytes(data)
    write_immutable(folder/'validation_audit.json',audit)
    ledger=dict(review_id=review_id,submission_sha256=digest(path.read_bytes()),baseline_sha256=digest(baseline_path.read_bytes()),
        annotation_ids=[a['id'] for a in annotations],blind_rehearsal=blind,prior_pilot_exposure=True,
        source_flags_cleared=False,training_approved=False,independent_claim='Annotator asserted no AI/prior-label exposure' if blind else 'Non-independent assisted review',
        history_policy='Append-only; prior judgments and source/evidence gates remain. Blind rehearsal is not final confirmatory evaluation.')
    if approval:
        ledger.update(training_approved=True,human_independent_check=True,blind_independent_annotation=False,
            approval_sha256=digest(approval_json.read_bytes()),training_policy_version='experimental-training-2.0.0',
            independent_claim='Independent human checking of assisted preparation; no blind independent annotation claimed.')
    write_immutable(folder/'ledger.json',ledger)
    return ledger


def main():
    parser=argparse.ArgumentParser();parser.add_argument('csv',type=__import__('pathlib').Path)
    parser.add_argument('--approval-json',type=__import__('pathlib').Path);parser.add_argument('--review-id',required=True);parser.add_argument('--blind',action='store_true')
    args=parser.parse_args();print(json.dumps(import_return(args.csv,args.review_id,args.blind,args.approval_json),indent=2))

if __name__=='__main__':main()
