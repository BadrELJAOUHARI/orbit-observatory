"""Record grants cannot invent checks or waive undocumented source/scope defects."""
import json,tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch
from orbit_data.training import eligible_training_rows
from orbit_data.authorized_dataset import authorization,validate_clearances,assess
from orbit_data.validation import digest


class AuthorizationClearanceTests(unittest.TestCase):
 def test_legacy_assistance_can_be_authorized_without_new_independent_check(self):
  row=dict(event_id='TEST',origin='ai_assisted_reviewed',review_status='reviewed_non_independent',schema_version='1.2.0',human_independent_check=None,
   training_policy_version='experimental-training-3.0.0',record_scoped_authorization_verified=True,training_approval_id='TEST-GRANT',ai_assisted=True,
   blind_independent_annotation=False,independent_human=False,training_approved=True,source_eligibility_cleared=True,text_quality_cleared=True,scope_cleared=True,label='support')
  good,bad=eligible_training_rows([row],dict(excluded_from_training_and_tuning_event_ids=[]))
  self.assertEqual(good,[row]);self.assertFalse(bad);self.assertIsNone(row['human_independent_check'])
  for field,value in [('record_scoped_authorization_verified',False),('training_approved',False),('source_eligibility_cleared',False),('scope_cleared',False),('label','unresolved'),('blind_independent_annotation',True)]:
   self.assertFalse(eligible_training_rows([dict(row,**{field:value})],dict(excluded_from_training_and_tuning_event_ids=[]))[0])
 def test_grant_lists_exact_records_without_approving_unresolved_targets(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'app';out=Path(tmp)/'out';root.mkdir()
   base=[dict(candidate_id='TEST-A'),dict(candidate_id='TEST-B')]
   anns={'TEST-A':dict(id='ANNOTATION-A',annotator_id='TEST',origin='ai_assisted_reviewed',label='no_stance'),
         'TEST-B':dict(id='ANNOTATION-B',annotator_id='TEST',origin='ai_assisted_reviewed',label='unresolved',human_independent_check=True)}
   before=copy.deepcopy(anns)
   with patch('orbit_data.authorized_dataset.ROOT',root),patch('orbit_data.authorized_dataset.OUTPUT',out):g=authorization(base,anns,{'TEST-REVIEW':'a'*64})
   self.assertEqual(anns,before);self.assertIsNone(g['records'][0]['existing_human_independent_check']);self.assertFalse(g['records'][1]['supervised_training_approved'])
   self.assertEqual([r['annotation_id'] for r in g['records']],['ANNOTATION-A','ANNOTATION-B'])
 def test_documentary_clearance_hash_and_quote_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'app';root.mkdir();evidence=Path(tmp)/'evidence.txt';evidence.write_text('TEST adopted conclusion.')
   base=[dict(candidate_id='TEST',quality_flags='EU_common_position_review',text_sha256='a'*64)]
   d=dict(id='TEST-CLEARANCE',candidate_id='TEST',source_text_sha256='a'*64,cleared_flags=['EU_common_position_review'],cleared_checks=['source_eligibility'],
     label_changed=False,independent_human=False,criterion_satisfied='Synthetic adopted position',evidence=[dict(path='evidence.txt',sha256=digest(evidence.read_bytes()),start=0,end=4,exact_text='TEST')])
   with patch('orbit_data.authorized_dataset.ROOT',root):
    validate_clearances([d],base)
    for bad in [dict(d,label_changed=True),dict(d,independent_human=True),dict(d,cleared_flags=['NONEXISTENT'])]:
     with self.assertRaises(ValueError):validate_clearances([bad],base)
    evidence.write_text('CHANGED')
    with self.assertRaises(ValueError):validate_clearances([d],base)
 def test_clearance_does_not_change_label_or_remove_scope_hold(self):
  source=dict(candidate_id='TEST',event_id='EVENT',quality_flags='EU_common_position_review;scope_hold_W1')
  row=dict(human_source_eligibility='needs_review',human_text_quality='usable',human_attribution='attributable',human_scope='partial_scope')
  a=dict(label='unresolved');split=dict(excluded_from_training_and_tuning_event_ids=[],reserved_leakage_group_ids=[])
  d=dict(candidate_id='TEST',id='CLEAR',cleared_flags=['EU_common_position_review'],cleared_checks=['source_eligibility'])
  reasons,flags,checks,applied=assess(source,row,a,'GROUP',split,[d],True)
  self.assertTrue(checks['source_eligibility']);self.assertEqual(flags,['scope_hold_W1']);self.assertEqual(a['label'],'unresolved')
  self.assertIn('excluded_supervised_target:unresolved',reasons);self.assertIn('preserved:scope_hold_W1',reasons)
 def test_defective_span_requires_revision_not_training_permission(self):
  source=dict(candidate_id='TEST',event_id='E',quality_flags='OCR');row=dict(human_source_eligibility='eligible',human_text_quality='defective',human_attribution='attributable',human_scope='exact_target_met')
  d=dict(candidate_id='TEST',id='C',cleared_flags=['OCR'],cleared_checks=['text_quality'])
  with self.assertRaises(ValueError):assess(source,row,dict(label='support'),'G',dict(excluded_from_training_and_tuning_event_ids=[],reserved_leakage_group_ids=[]),[d],True)

if __name__=='__main__':unittest.main()
