import csv,json,unittest,tempfile
from unittest.mock import patch
from jsonschema import Draft202012Validator
from pathlib import Path
from orbit_data.component_review import interpret,PACKET,SCOPE_HOLDS
from orbit_data.focal_review import relevant
from orbit_data.focal_retrieval import OUT
from orbit_data.review_import import select_baseline,audit_return
from orbit_data.validation import digest,ROOT

def example(lens,text):return dict(lens_id=lens,exact_passage=text,context_before='',context_after='',start=0,event_date='2024-01-01')

class ComponentRules(unittest.TestCase):
 def test_integrity_direction_is_separate_from_scope_and_annexation(self):
  v=interpret(example('territorial_recognition','We reaffirm Ukraine’s sovereignty and territorial integrity.'))
  self.assertEqual((v['direction'],v['scope'],v['annexation']),('support','unspecified','not_addressed'))
 def test_direction_does_not_silently_release_w1(self):
  v=interpret(example('troop_withdrawal','Russia must withdraw from Ukrainian territory.'))
  self.assertEqual((v['direction'],v['scope']),('support','unspecified'))
 def test_conditional_support_is_not_automatically_mixed(self):
  v=interpret(example('troop_withdrawal','We call for Russian withdrawal from Ukrainian territory if agreed guarantees are implemented.'))
  self.assertEqual(v['direction'],'support');self.assertIn('if agreed guarantees',v['conditions'])
 def test_equipping_for_defence_is_contextual_aid(self):
  v=interpret(example('military_assistance','We will continue equipping Ukraine to defend itself.'))
  self.assertEqual((v['direction'],v['expression']),('support','contextually_implied'))
 def test_peace_and_humanitarian_aid_are_not_military_or_withdrawal(self):
  self.assertFalse(relevant('troop_withdrawal','We urge all parties to pursue peace.','Ukraine','2024-01-01'))
  self.assertFalse(relevant('military_assistance','We have sent humanitarian supplies to Ukraine.','','2024-01-01'))
 def test_explicit_negation_is_preserved(self):
  self.assertEqual(interpret(example('territorial_recognition',"We do not support Ukraine's sovereignty."))['direction'],'oppose')

class ComponentArtifacts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=json.loads((PACKET/'review_queue.json').read_text());cls.refs=json.loads((PACKET/'source_refs.json').read_text())
 def test_component_quality_offsets_and_basis(self):
  schema=Draft202012Validator(json.loads((ROOT/'schemas/acquisition-v2/component.schema.json').read_text()))
  for r in self.refs.values():
   schema.validate(r)
   t=Path(r['source_text_path']).read_text();v=r['experimental_components']
   self.assertEqual(digest(t.encode()),r['text_sha256']);self.assertEqual(t[r['start']:r['end']],r['exact_passage']);self.assertEqual(t[v['basis_start']:v['basis_end']],v['basis'])
   self.assertFalse(r['technical_quality_flags']);self.assertFalse(r['strict_target_eligible']);self.assertFalse(r['training_approved']);self.assertTrue(set(r['target_scope_flags'])<=SCOPE_HOLDS)
   self.assertEqual(r['event_role'],'development_only');self.assertNotIn('strength',v)
 def test_return_validator_preserves_component_target_and_strict_fields(self):
  with (PACKET/'orbit-development-review.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
  path,base=select_baseline(rows);self.assertEqual(path.parent,PACKET);self.assertFalse(audit_return(rows,base)['fatal_conflicts'])
  rows[0]['strict_target_status']='silently changed';self.assertTrue(audit_return(rows,base)['fatal_conflicts'])
 def test_evaluation_groups_absent_from_both_views(self):
  split=json.loads((OUT/'split_assignments.json').read_text());reserved={x['group_id'] for x in split.values() if x['role']=='evaluation_reserved'}
  self.assertFalse(reserved & {r['leakage_group_id'] for r in self.rows})
 def test_component_import_is_idempotent_and_cannot_create_strict_labels(self):
  from orbit_data import component_review
  with tempfile.TemporaryDirectory(prefix='orbit-synthetic-component-',dir='/tmp') as directory:
   root=Path(directory);rows=[dict(r) for r in self.rows]
   rows[0].update(human_label='support',human_annotator_id='SYNTHETIC_TEST_ONLY',human_review_notes='Synthetic importer fixture; not a research judgment.')
   path=root/'synthetic.csv'
   with path.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
   with patch.object(component_review,'ROOT',root/'app'):
    first=component_review.import_component_return(path,'synthetic-test');second=component_review.import_component_return(path,'synthetic-test')
   self.assertEqual(first,second);self.assertEqual(first['reviewed'],1);self.assertEqual(first['strict_annotations_created'],0);self.assertEqual(first['training_approvals_created'],0)

if __name__=='__main__':unittest.main()
