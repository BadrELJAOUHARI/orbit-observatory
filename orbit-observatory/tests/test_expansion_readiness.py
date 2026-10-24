"""Return auditing, event isolation, extraction provenance and baseline smoke checks."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from orbit_data.review_import import audit_return
from orbit_data.training import check_baseline_fixtures,train_baseline
from orbit_data.expansion import clear_catalog,validate_expansion
from orbit_data.expansion_collect import extract_pdf,landing_metadata
from orbit_data.validation import digest

class ExpansionTests(unittest.TestCase):
 def test_all_return_conflicts_are_reported(self):
  base=[dict(candidate_id=str(i),row_id=f'R{i}',exact_passage='Frozen.',event_role='development_only',existing_label='support',existing_annotation_id='prior',human_label='',human_annotator_id='',human_review_notes='',human_independent='false') for i in range(3)]
  changed=[dict(r,human_label='no_stance',human_annotator_id='TEST',human_review_notes='Test only.') for r in base]
  changed[0]['exact_passage']='Changed';changed[1]['human_independent']='true';changed.append(changed[0])
  audit=audit_return(changed,base)
  self.assertTrue(any(e['reason']=='duplicate_candidate' for e in audit['fatal_conflicts']))
  self.assertTrue(any(e['reason']=='immutable_fields_changed' for e in audit['fatal_conflicts']))
  self.assertTrue(any('independent' in e.get('detail','') for e in audit['fatal_conflicts']))
  self.assertEqual(len(audit['prior_label_differences']),4)
 def test_dated_copy_is_not_an_additional_event(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'speech.txt').write_text('Statement delivered 20 September 2017. Synthetic source.')
   docs=[dict(document_id=f'TEST-{y}',actor_id='EU',year=y,language='en',text_sha256='a'*64,text_path='speech.txt',quality_issues=[],event_role='development_only',duplicate_of=None) for y in (2018,2017)]
   before=copy.deepcopy(docs)
   with patch('orbit_data.expansion.OUT',root):result=clear_catalog(docs)
   self.assertEqual(result[0]['duplicate_of'],'TEST-2017');self.assertFalse(result[0]['event_identity_verified'])
   self.assertIsNone(result[1]['duplicate_of']);self.assertTrue(result[1]['event_identity_verified'])
   self.assertEqual(docs,before)
 def test_reserved_copy_reserves_actual_event_cluster(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'speech.txt').write_text('Synthetic statement 20 September 2017.')
   docs=[dict(document_id=f'TEST-{y}',actor_id='EU',year=y,language='en',text_sha256='a'*64,text_path='speech.txt',quality_issues=[],event_role='evaluation_reserved' if y==2018 else 'development_only',duplicate_of=None) for y in (2018,2017)]
   with patch('orbit_data.expansion.OUT',root):result=clear_catalog(docs)
   self.assertTrue(all(d['event_role']=='evaluation_reserved' for d in result))
 def test_other_conflict_is_diagnostic_not_main_queue(self):
  from orbit_data.expansion import screen_retrieval
  candidates=[dict(id='TEST-GAZA',reading_text='The conflict in Gaza is widening.',quality_issues=[]),dict(id='TEST-UKRAINE',reading_text='We condemn aggression against Ukraine.',quality_issues=[])]
  accepted,rejected=screen_retrieval(candidates)
  self.assertEqual([c['id'] for c in accepted],['TEST-UKRAINE'])
  self.assertEqual(rejected[0]['retrieval_disposition'],'rejected_other_conflict')
 def test_exact_offsets_roles_and_duplicate_guards(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);text='Synthetic Ukraine border evidence.\nSecond sentence.'
   (root/'text.txt').write_text(text);(root/'raw.bin').write_bytes(b'test')
   doc=dict(document_id='TEST-DOC',event_id='TEST-EVENT',actor_id='USA',actor_role='focal',event_date='2024-01-01',issuer='TEST ONLY',canonical_url='https://example.org/test',resolved_url='https://example.org/test',language='en',raw_path='raw.bin',raw_sha256=digest(b'test'),text_path='text.txt',text_sha256=digest(text.encode()),retrieved_at='2026-10-23T00:00:00Z',quality_issues=[],event_role='development_only',duplicate_of=None,event_identity_verified=True)
   claim=dict(record_type='expansion_candidate',schema_version='1.0.0',id='TEST-CLAIM',document_id='TEST-DOC',event_id='TEST-EVENT',actor_id='USA',lens_id='territorial_recognition',text_sha256=doc['text_sha256'],start=0,end=len(text),exact_passage=text,reading_text=text.replace('\n',' '),source_indices=list(range(len(text))),quality_issues=[],origin='retrieval_not_prediction',scoring_eligible=False,training_approved=False)
   roles={'TEST-EVENT':'development_only'}
   validate_expansion([doc],[claim],roles,root)
   for bad in [dict(claim,end=len(text)-1),dict(claim,reading_text='Altered'),dict(claim,event_id='OTHER')]:
    with self.assertRaises(ValueError):validate_expansion([doc],[bad],roles,root)
   with self.assertRaises(ValueError):validate_expansion([doc],[claim,claim],roles,root)
   with self.assertRaises(ValueError):validate_expansion([dict(doc,event_role='evaluation_reserved')],[claim],roles,root)
 def test_supported_plain_extraction_never_rewrites_text(self):
  pages=['Synthetic first sentence. '*20,'Synthetic continuation. '*20]
  text,history,issues=extract_pdf(b'',pages,'en')
  self.assertIn('\n',text);self.assertEqual(history,[]);self.assertEqual(issues,[])
 def test_baseline_fit_is_strictly_fixture_only(self):
  result=check_baseline_fixtures()
  self.assertEqual(len(result['classes']),5);self.assertTrue(result['fit_predict_passed'])
  self.assertFalse(result['real_corpus_training_executed']);self.assertFalse(result['real_world_performance_claim'])
  with self.assertRaises(ValueError):train_baseline(dict(train=[],validation=[],heldout_event_ids=[]))

if __name__=='__main__':unittest.main()
