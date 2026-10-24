"""Synthetic provenance, evidence gates, copy isolation and per-lens readiness tests."""
import copy,json,tempfile,unittest,threading,urllib.request
from pathlib import Path
from orbit_data.review_import import validate_approval
from orbit_data.training import eligible_training_rows,assert_training_ready
from orbit_data.validation import validate_record
from orbit_data.experimental_dataset import evidence_reasons,leakage_groups
from orbit_data.experimental_baseline import plan_lens,validate_prediction
from orbit_data.backend import EvidenceStore,handler_class
from http.server import ThreadingHTTPServer


def annotation():
 return dict(record_type='annotation',schema_version='1.3.0',id='TEST-ANNOTATION',claim_id='TEST-CLAIM',origin='ai_assisted_reviewed',annotator_id='TEST_REVIEWER',codebook_version='consolidated-v1',label='support',review_status='reviewed_non_independent',created_at='2026-10-23T00:00:00Z',rationale='Synthetic test only.',supersedes=None,batch_id='TEST-ROW',review_notes='Synthetic human check, not actual research.',review_provenance='Synthetic AI-assisted origin, not blind.',ai_assisted=True,independent_human=False,scoring_status='not_scored_pending_quality_review',human_independent_check=True,training_approved=True,blind_independent_annotation=False,training_approval_id='TEST-APPROVAL',training_policy_version='experimental-training-2.0.0')


def training_row():
 return dict(annotation(),event_id='TEST-EVENT',source_eligibility_cleared=True,text_quality_cleared=True,scope_cleared=True)


class HumanVerifiedTrainingTests(unittest.TestCase):
 def test_schema_preserves_assistance_and_separate_independence(self):
  a=annotation();validate_record(a)
  for key,value in [('origin','human'),('independent_human',True),('blind_independent_annotation',True),('ai_assisted',False)]:
   with self.assertRaises(Exception):validate_record(dict(a,**{key:value}))
 def test_record_scoped_approval_and_blind_flag(self):
  row=dict(candidate_id='TEST-CLAIM',human_label='support',human_annotator_id='TEST_REVIEWER',human_independent='false')
  baseline=[dict(candidate_id='TEST-CLAIM',existing_annotation_id='')]
  approval=dict(reviewer_id='TEST_REVIEWER',candidate_ids=['TEST-CLAIM'],human_independent_check=True,training_approved=True,ai_assisted_initial_annotation=True,blind_independent_annotation=False)
  result=validate_approval(approval,[row],baseline)
  self.assertFalse(result['source_holds_cleared']);self.assertFalse(result['blind_independent_annotation'])
  for bad in [dict(approval,candidate_ids=[]),dict(approval,candidate_ids=['TEST-CLAIM','TEST-CLAIM']),dict(approval,blind_independent_annotation=True)]:
   with self.assertRaises(ValueError):validate_approval(bad,[row],baseline)
  with self.assertRaises(ValueError):validate_approval(approval,[row],[dict(baseline[0],existing_annotation_id='PRIOR')])
 def test_new_policy_accepts_assisted_check_without_human_only_origin(self):
  r=training_row();good,bad=eligible_training_rows([r],dict(excluded_from_training_and_tuning_event_ids=[]))
  self.assertEqual(good,[r]);self.assertEqual(bad,{})
  for key,value in [('human_independent_check',False),('training_approved',False),('source_eligibility_cleared',False),('text_quality_cleared',False),('scope_cleared',False),('label','unresolved'),('label','not_applicable')]:
   self.assertEqual(eligible_training_rows([dict(r,**{key:value})],dict(excluded_from_training_and_tuning_event_ids=[]))[0],[])
 def test_prior_assisted_review_is_not_automatically_approved(self):
  r=training_row();r['schema_version']='1.2.0';r.pop('human_independent_check')
  self.assertFalse(eligible_training_rows([r],dict(excluded_from_training_and_tuning_event_ids=[]))[0])
 def test_source_and_scope_holds_survive_approval(self):
  row=dict(event_id='TEST-EVENT',quality_flags='OCR_text_requires_visual_review',quarantine='true',human_source_eligibility='eligible',human_text_quality='usable',human_attribution='attributable',human_scope='exact_target_met')
  reasons=evidence_reasons(row,annotation(),set(),'TEST-GROUP',set())
  self.assertIn('existing_source_or_text_hold',reasons)
  row.update(quality_flags='excluded_scope_hold_W1',human_scope='partial_scope')
  self.assertIn('preserved_scope_or_W1_hold',evidence_reasons(row,annotation(),set(),'TEST-GROUP',set()))
 def test_no_stance_is_a_class_not_an_alignment_value(self):
  r=training_row();r.update(label='no_stance',alignment_score=None)
  self.assertEqual(eligible_training_rows([r],dict(excluded_from_training_and_tuning_event_ids=[]))[0],[r])
  self.assertIsNone(r['alignment_score'])
 def test_mirrors_translations_and_joint_events_stay_grouped(self):
  docs=[dict(id='A',event_id='A-EVENT',text_sha256='first'),dict(id='B',event_id='B-EVENT',text_sha256='second',translation_of='A'),dict(id='C',event_id='C-EVENT',text_sha256='third',duplicate_of='B'),dict(id='D',event_id='D-EVENT',joint_statement_id='JOINT'),dict(id='E',event_id='E-EVENT',joint_statement_id='JOINT')]
  groups=leakage_groups(docs,[],{'A-EVENT'})
  mapping=groups['event_groups'];self.assertEqual(mapping['A-EVENT'],mapping['C-EVENT']);self.assertEqual(mapping['D-EVENT'],mapping['E-EVENT'])
  self.assertIn(mapping['B-EVENT'],groups['reserved_leakage_group_ids'])
 def test_substantial_cross_event_passage_overlap_is_grouped(self):
  phrase=' '.join('syntheticword'+str(i) for i in range(20))
  claims=[dict(id='A',event_id='A',reading_text=phrase),dict(id='B',event_id='B',reading_text=phrase+' synthetic ending')]
  groups=leakage_groups([],claims,{'A'})
  self.assertEqual(groups['event_groups']['A'],groups['event_groups']['B'])
 def test_connected_group_leakage_is_rejected_even_if_event_ids_differ(self):
  a=dict(training_row(),leakage_group_id='SAME');b=dict(a,event_id='OTHER',label='no_stance')
  with self.assertRaises(ValueError):assert_training_ready(dict(train=[a,dict(a,event_id='THIRD',leakage_group_id='THIRD',label='no_stance')],validation=[b],heldout_event_ids=[]))
 def test_two_classes_in_one_event_does_not_pass(self):
  rows=[dict(candidate_id='A',event_id='E',leakage_group_id='G',label='support'),dict(candidate_id='B',event_id='E',leakage_group_id='G',label='no_stance')]
  self.assertFalse(plan_lens(rows)['eligible_to_run'])
 def test_two_events_with_event_specific_classes_does_not_pass(self):
  rows=[dict(candidate_id='A',event_id='A',leakage_group_id='A',label='support'),dict(candidate_id='B',event_id='B',leakage_group_id='B',label='no_stance')]
  self.assertFalse(plan_lens(rows)['eligible_to_run'])
 def test_feasible_groups_keep_classes_and_ids_separate(self):
  rows=[dict(candidate_id=e+label,event_id=e,leakage_group_id=e,label=label) for e in ['A','B'] for label in ['support','no_stance']]
  plan=plan_lens(rows);self.assertTrue(plan['eligible_to_run'])
  for fold in plan['folds']:self.assertFalse(set(fold['train_candidate_ids'])&set(fold['validation_candidate_ids']))
 def test_feasible_training_branch_saves_only_temporary_test_models(self):
  # Artificial software fixture, not additional research labels or reported metrics.
  from unittest.mock import patch
  from orbit_data.experimental_baseline import run
  with tempfile.TemporaryDirectory(prefix='orbit-test-only-') as tmp:
   root=Path(tmp);(root/'dataset_manifest.json').write_text('{"test_fixture":true}')
   rows=[]
   for event in ['TEST-A','TEST-B']:
    for label,words in [('support','TEST_ONLY endorses artificial measure'),('no_stance','TEST_ONLY describes fictional weather')]:
     rows.append(dict(training_row(),candidate_id=event+label,event_id=event,leakage_group_id=event,label=label,
      lens_id='sanctions',proposition='TEST_ONLY fictional measure',passage=words,actor_id='TEST_ONLY',actor_role='focal',text_sha256='a'*64))
   split=dict(excluded_from_training_and_tuning_event_ids=['TEST-HELD'],reserved_leakage_group_ids=[])
   with patch('orbit_data.experimental_baseline.OUTPUT',root),patch('orbit_data.experimental_baseline.load_frozen',return_value=(rows,split,{'files':{'dataset.json':'a'*64}})):
    report=run(root/'trial')
   self.assertEqual(report['trained_lenses'],['sanctions']);self.assertEqual(len(list((root/'trial').rglob('*.joblib'))),3)
   predictions=json.loads((root/'trial/experimental_predictions.json').read_text());self.assertEqual(len(predictions),4)
   self.assertTrue(all(p['alignment_score'] is None and not p['calibrated'] for p in predictions))
   self.assertFalse(report['reserved_evaluation_used']);self.assertFalse(report['public_scores_changed'])
   for fold in report['lenses']['sanctions']['folds']:
    majority=min(fold['train_class_counts'],key=lambda k:(-fold['train_class_counts'][k],k))
    self.assertEqual(fold['majority_label'],majority)
   self.assertIn('majority_comparator',report['lenses']['sanctions'])
 def test_local_api_exposes_evidence_and_empty_predictions_separately(self):
  store=EvidenceStore.__new__(EvidenceStore);store.evidence=[dict(candidate_id='TEST',actor_id='USA',lens_id='sanctions',training_included=True,alignment_score=None)]
  store.index={'TEST':store.evidence[0]};store.predictions=[];store.dataset_hash='a'*64;store.report={'trained_lenses':[]}
  server=ThreadingHTTPServer(('127.0.0.1',0),handler_class(store));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/experimental-predictions') as response:r=json.load(response)
   self.assertEqual(r['items'],[]);self.assertIsNone(r['alignment_score']);self.assertFalse(r['public_score_connection'])
   self.assertEqual(store.query('/api/evidence',{'limit':['bad']})[0],400)
   self.assertEqual(store.query('/api/evidence/UNKNOWN',{})[0],404)
  finally:server.shutdown();server.server_close()
 def test_experimental_predictions_cannot_claim_calibration_or_neutral_score(self):
  pred=dict(record_type='experimental_prediction',schema_version='1.0.0',origin='trained_baseline_experiment',candidate_id='TEST',event_id='TEST',actor_id='USA',actor_role='focal',lens_id='sanctions',text_sha256='a'*64,predicted_label='no_stance',probabilities={'support':.2,'no_stance':.8},model_id='TEST',dataset_manifest_sha256='b'*64,split_role='development_validation_out_of_group',calibrated=False,validated_for_publication=False,alignment_score=None,review_status='machine_unreviewed')
  validate_prediction(pred)
  for key,value in [('alignment_score',0),('calibrated',True),('validated_for_publication',True)]:
   with self.assertRaises(Exception):validate_prediction(dict(pred,**{key:value}))

if __name__=='__main__':unittest.main()
