import csv,json,unittest
from orbit_data.protocol_v2 import OUT,validate,eligible
class Protocol(unittest.TestCase):
 def test_inventory(self):
  r=json.loads((OUT/'rows.json').read_text());self.assertEqual(len(r),780);self.assertEqual(len({x['candidate_id'] for x in r}),780);self.assertTrue(all(x['event_role']=='development_only' for x in r));self.assertEqual(sum(x['task_kind']=='component' for x in r),171)
 def test_separate_components_and_approval(self):
  ref={'quality_flags':['partial_territorial_scope'],'event_role':'development_only'}
  a={'candidate_id':'x','components':{'integrity_direction':'support'}}
  self.assertTrue(eligible(a,'integrity_direction',{'x':['integrity_direction']},ref));self.assertFalse(eligible(a,'annexation_direction',{'x':['integrity_direction']},ref));ref['quality_flags'].append('translation_review');self.assertFalse(eligible(a,'integrity_direction',{'x':['integrity_direction']},ref))
 def test_no_approval_no_training_and_no_legacy_mutation(self):
  with (OUT/'review.csv').open(encoding='utf-8-sig',newline='') as f:r=list(csv.DictReader(f))
  self.assertEqual(validate(r),[]);r[0]['human_label']='support'
  with self.assertRaises(ValueError):validate(r)
 def test_independent_axis_values(self):
  with (OUT/'review.csv').open(encoding='utf-8-sig',newline='') as f:r=list(csv.DictReader(f))
  row=next(x for x in r if x['task_kind']=='component' and x['lens_id']=='territorial_recognition');row.update(human_integrity_direction='support',human_annexation_direction='unresolved',human_annotator_id='SYNTHETIC',human_review_notes='Synthetic, never imported')
  a=validate(r);self.assertEqual(a[0]['components']['integrity_direction'],'support');self.assertEqual(a[0]['components']['annexation_direction'],'unresolved');self.assertFalse(a[0]['training_approved'])
 def test_export_approved_component_does_not_require_annexation(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from orbit_data import protocol_v2 as mod
  refs=json.loads((OUT/'source_refs.json').read_text());cid=next(k for k,v in refs.items() if k.startswith('component-') and v['lens_id']=='territorial_recognition')
  with tempfile.TemporaryDirectory(prefix='orbit-synthetic-v2-',dir='/tmp') as tmp:
   root=Path(tmp);folder=root/'.local/consolidated-component-returns/synthetic';folder.mkdir(parents=True)
   (folder/'records.json').write_text(json.dumps([{'candidate_id':cid,'components':{'integrity_direction':'support','expression':'explicit'},'origin':'ai_assisted_reviewed'}]))
   approval=root/'synthetic-approval.json';approval.write_text(json.dumps({'protocol':'components-v2.0.0','approved_by':'SYNTHETIC_TEST_ONLY','approvals':{cid:['integrity_direction','annexation_direction']}}))
   with patch.object(mod,'ROOT',root/'app'):result=mod.export_approved(approval)
   self.assertEqual(result['included'],1);self.assertEqual(result['excluded'],1);self.assertFalse(result['models_trained'])
   data=json.loads((Path(result['path'])/'dataset.json').read_text());self.assertEqual(data[0]['component_target'],'territorial_recognition:integrity_direction');self.assertIsNone(data[0]['alignment_score'])
