"""Append the five reviewed repairs and Badr_A's explicit W1 decision."""
import json
from .validation import ROOT, digest, validate_dataset
from .reviewed import write_immutable
from .followup import overlay_history
from .collect import utcnow


def record_third_review(cache,batch):
    folder=ROOT/'annotations/v1/reviews/Badr_A'
    submission_path=folder/'submission-0003.json'
    s=json.loads(submission_path.read_text())
    history=overlay_history(batch)
    base=json.loads((cache/'records.json').read_text())
    ledger_path=folder/'review-0003.review.json'
    if ledger_path.exists():
        ledger=json.loads(ledger_path.read_text())
        if ledger['submission_sha256']!=digest(submission_path.read_bytes()): raise ValueError('Submission changed')
        private=batch/'reviews/Badr_A/review-0003/overlay_records.json'
        if ledger['annotations']!=json.loads(private.read_text()): raise ValueError('Ledger/overlay mismatch')
        validate_dataset(base+history,cache)
        return ledger
    tasks=json.loads((batch/'reviews/Badr_A/review-0002/repaired_tasks.json').read_text())
    mapping={t['row_id']:t for t in tasks}
    if s['ai_assisted'] is not True or s['independent_human'] is not False or s['annotator_id']!='Badr_A':
        raise ValueError('Non-independent reviewed provenance required')
    if len(s['judgments'])!=5 or {j['batch_id'] for j in s['judgments']}!=set(mapping): raise ValueError('Batch mismatch')
    annotations=[]
    now=utcnow()
    for j in s['judgments']:
        row=mapping[j['batch_id']]
        annotations.append(dict(schema_version='1.2.0',record_type='annotation',
          id='annotation-'+digest(f"Badr_A:review-0003:{row['candidate_id']}:{digest(submission_path.read_bytes())}".encode()),
          claim_id=row['candidate_id'],batch_id=row['row_id'],origin='ai_assisted_reviewed',annotator_id='Badr_A',
          codebook_version=row['codebook_version'],label=j['label'],review_status='reviewed_non_independent',created_at=now,
          rationale=j['review_notes'],review_notes=j['review_notes'],supersedes=None,
          review_provenance=s['review_provenance'],ai_assisted=True,independent_human=False,
          scoring_status='not_scored_pending_quality_review'))
    validate_dataset(base+history+annotations,cache)
    prior_conflict=json.loads((folder/'review-0002.scope_conflict.json').read_text())
    decision=dict(protocol_version='scope-decision-1.0.2',decision_origin='explicit_Badr_A_instruction',selected_option='W1',
                  configured_targets_changed=False,comprehensive_withdrawal_scope_required=True,
                  equivalent_explicit_comprehensive_wording_allowed=True,absence_of_exception_alone_sufficient=False,
                  territorial_recognition_broadened=False,W2_applied=False,
                  supersedes_pending_decision='codebooks/v1.0.1/status.json',
                  prior_scope_conflict='annotations/v1/reviews/Badr_A/review-0002.scope_conflict.json',
                  annotation_id=prior_conflict['annotation_id'],candidate_id=prior_conflict['candidate_id'],
                  preserved_label='support',scoring_status='excluded_scope_hold_W1',
                  preserved_hold_reason=prior_conflict['issue'],scope_conflict_status='resolved_rule_choice_evidence_still_insufficient',
                  B09_B10_reason_class='scope_insufficiency_not_political_or_model_ambiguity')
    write_immutable(ROOT/'codebooks/v1.0.2/decision.json',decision)
    write_immutable(batch/'reviews/Badr_A/review-0003/overlay_records.json',annotations)
    ledger=dict(review_id='review-0003',recorded_at=now,annotator_id='Badr_A',
                submission_sha256=digest(submission_path.read_bytes()),previous_review_sha256=digest((folder/'review-0002.review.json').read_bytes()),
                annotations=annotations,scope_decision='codebooks/v1.0.2/decision.json',
                total_assisted_reviewed_decisions=16,independent_annotation_count=0,
                history_policy='Append only. Earlier labels, scope-conflict reason and original evidence preserved.')
    write_immutable(ledger_path,ledger)
    return ledger
