import csv,json,re,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from orbit_data.focal_retrieval import OUT,OLD,wire_url
from orbit_data.focal_review import PACKET,relevant,scope_complete,windows,reading_map,speaker_for
from orbit_data.focal_recovery import clear_claim
from orbit_data.validation import ROOT,digest
from orbit_data.review_import import select_baseline,audit_return
from orbit_data.acquisition_sprint import military_recipient_is_ukraine

class GateTests(unittest.TestCase):
    def test_unicode_urls_are_encoded_once(self):
        u='https://www.mfa.gov.tr/hüseyin-müftüoğlu.en.mfa'
        encoded=wire_url(u);self.assertIn('h%C3%BCseyin',encoded);self.assertEqual(wire_url(encoded),encoded);self.assertIn('hüseyin',u)
    def test_nuclear_use_and_armed_groups_are_not_ukrainian_aid(self):
        self.assertFalse(military_recipient_is_ukraine('The threat or use of nuclear weapons narrows the prohibition to the Ukraine context only.'))
        self.assertFalse(military_recipient_is_ukraine('Russia must suspend support for illegal armed groups in Ukraine and stop the flow of weapons across the border.'))
        self.assertTrue(military_recipient_is_ukraine('We provide Ukraine with weapons and financial support.'))
        self.assertTrue(military_recipient_is_ukraine('Our political, military, financial and humanitarian support for Ukraine remains steadfast.'))
    def test_caucasus_history_is_not_2022_responsibility(self):
        self.assertFalse(relevant('invasion_responsibility','During the invasion of the Caucasus by Tsarist Russia in the 19th century, many people died.','We support Ukraine.', '2022-05-18'))
        self.assertFalse(relevant('invasion_responsibility','This huge exodus of people moving towards the western part of Ukraine led to extraordinary pressure on the border crossing infrastructure.','','2022-03-17'))
    def test_economic_effects_are_not_sanctions_support(self):
        self.assertFalse(relevant('sanctions','Many energy producers are sanctioned, making the market tight and increasing prices.','Russia and Ukraine were discussed.','2024-08-23'))
    def test_annexure_and_recognizing_achievements_are_not_territorial_policy(self):
        self.assertFalse(relevant('territorial_recognition','A list of students is enclosed as Annexure I. Students have returned due to the Ukraine crisis.','','2022-03-25'))
        self.assertFalse(relevant('territorial_recognition','The leaders discussed recognizing the value of India joining the Nuclear Suppliers Group.','Ukraine was discussed.','2026-05-22'))
        self.assertFalse(relevant('territorial_recognition','Russia wants assurances that missiles will not be deployed near its borders.','Ukraine','2022-03-11'))
        self.assertFalse(relevant('territorial_recognition','The leaders support a free Indo-Pacific with respect for sovereignty.','They discussed Ukraine.','2025-06-18'))
        self.assertFalse(relevant('territorial_recognition','Any connectivity that flouts sovereignty acquires strategic connotations.','Ukraine and Gaza were discussed.','2024-09-28'))
    def test_w1_unqualified_withdrawal_remains_insufficient(self):
        self.assertFalse(scope_complete('All Russian forces should withdraw from Ukraine.'))
        self.assertTrue(scope_complete('Russian forces must leave Ukraine within its internationally recognised borders.'))
    def test_physical_lines_reconstruct_complete_claim(self):
        t='We support Ukraine within its internationally\nrecognised borders and reject the annexation\nof Crimea.\nWe continue diplomatic talks.'
        ws=list(windows(t,0));self.assertTrue(any(t[a:b].startswith('We support') and t[a:b].endswith('Crimea.') for a,b in ws))
    def test_reading_aid_maps_around_pdf_header(self):
        t='We support Ukraine within its\nEUCO 1/22\nEN\ninternationally recognised borders.'
        reading,indices=reading_map(t,0,len(t),True)
        self.assertNotIn('EUCO',reading);self.assertIn('internationally recognised borders',reading)
        self.assertEqual(reading,''.join(' ' if t[i].isspace() else t[i] for i in indices))
    def test_reporter_and_official_turns_differ(self):
        d=dict(source_type='mea',title='Transcript of briefing',speaker='MEA')
        t='Suhasini: What does India think?\nHarsh Vardhan Shringla, Foreign Secretary: We seek dialogue.'
        self.assertIsNotNone(speaker_for(d,t,0)[1]);self.assertIsNone(speaker_for(d,t,t.index('Harsh'))[1])
    def test_interview_questions_and_parliamentary_questions_are_not_policy(self):
        d=dict(source_type='mea',title='English translation of interview',speaker='Minister',canonical_url='https://www.mea.gov.in/interviews?dtl/1')
        t='Q:\nDoes India oppose Russia sanctions?\nA:\nOur position is explained below.'
        self.assertIsNotNone(speaker_for(d,t,t.index('Does'))[1]);self.assertIsNone(speaker_for(d,t,t.index('Our'))[1])
        d['canonical_url']='https://www.mea.gov.in/lok-sabha?dtl/1';t='Will the Minister oppose sanctions?\nANSWER\nThe Government responds.'
        self.assertIsNotNone(speaker_for(d,t,0)[1]);self.assertIsNone(speaker_for(d,t,t.index('The Government'))[1])
    def test_turkish_minister_interview_preserves_speaker(self):
        d=dict(source_type='mfa',title='Interview of Minister Hakan Fidan',speaker='MFA')
        t='PRESENTER- What about Ukraine?\nFOREIGN MINISTER HAKAN FİDAN- We support its territorial integrity.'
        self.assertIsNotNone(speaker_for(d,t,0)[1]);self.assertIsNone(speaker_for(d,t,t.index('FOREIGN'))[1])
    def test_publishing_us_president_does_not_make_his_turn_indian(self):
        d=dict(source_type='mea',title='Media Statements by Prime Minister and President',speaker='MEA',canonical_url='https://www.mea.gov.in/media-briefings?dtl/1')
        t='Prime Minister Shri Narendra Modi: Welcome.\nPresident Barack Obama: We provide military supplies to Ukraine.'
        self.assertIsNone(speaker_for(d,t,0)[1]);self.assertIsNotNone(speaker_for(d,t,t.index('President'))[1])
    def test_source_only_clearance_does_not_transfer_labels(self):
        p='Today OFAC imposed sanctions on Russia for its invasion of Ukraine. More specifically:'
        r=dict(candidate_id='old',document_id='d',start=0,end=len(p),exact_passage=p,lens_id='sanctions',quality_flags=['incomplete_sentence_boundary'],actor_id='USA')
        d=dict(actor_id='USA',source_type='treasury',canonical_url='https://home.treasury.gov/test',text_sha256=digest(p.encode()),text_path='test',title='Statement')
        v,proofs,_=clear_claim(r,d,p)
        self.assertNotEqual(v['candidate_id'],r['candidate_id']);self.assertEqual(p[v['start']:v['end']],v['exact_passage']);self.assertFalse(v['human_label']);self.assertFalse(v['training_approved']);self.assertTrue(proofs)

class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads((PACKET/'review_queue.json').read_text());cls.refs=json.loads((PACKET/'source_refs.json').read_text())
    def test_original_561_packet_and_691_holds_unchanged(self):
        p=ROOT.parent/'.local/development-review-sprint-v1';m=json.loads((p/'manifest.json').read_text())
        for n,h in m['files'].items():self.assertEqual(digest((p/n).read_bytes()),h)
        m=json.loads((ROOT/'source_manifest/acquisition-sprint-v1/manifest.json').read_text())
        for n,h in m['artifacts'].items():self.assertEqual(digest((OLD/n).read_bytes()),h)
    def test_exact_offsets_context_reading_and_schema(self):
        validator=Draft202012Validator(json.loads((ROOT/'schemas/acquisition-v2/candidate.schema.json').read_text()))
        for r in self.refs.values():
            validator.validate(r);t=Path(r['source_text_path']).read_text();self.assertEqual(digest(t.encode()),r['text_sha256']);self.assertEqual(t[r['start']:r['end']],r['exact_passage'])
            self.assertEqual(r['reading_text'],''.join(' ' if t[i].isspace() else t[i] for i in r['reading_source_indices']))
            self.assertFalse(r['quality_flags']);self.assertFalse(r['human_label']);self.assertFalse(r['training_approved'])
        for r in self.rows:
            t=Path(self.refs[r['candidate_id']]['source_text_path']).read_text();self.assertEqual(t[int(r['context_start']):int(r['start'])],r['context_before']);self.assertEqual(t[int(r['end']):int(r['context_end'])],r['context_after'])
    def test_reserved_groups_absent(self):
        split=json.loads((OUT/'split_assignments.json').read_text());reserved={x['group_id'] for x in split.values() if x['role']=='evaluation_reserved'}
        old={r['candidate_id'] for r in json.loads((ROOT.parent/'.local/development-review-sprint-v1/review_queue.json').read_text())}
        self.assertFalse(reserved & {r['leakage_group_id'] for r in self.rows});self.assertFalse(old & set(self.refs))
    def test_clearances_have_reproducible_proof(self):
        docs={d['id']:d for d in json.loads((OLD/'source_event_manifest.json').read_text())};held={r['candidate_id']:r for r in json.loads((OLD/'held.json').read_text())}
        validator=Draft202012Validator(json.loads((ROOT/'schemas/acquisition-v2/clearance.schema.json').read_text()))
        for c in json.loads((OUT/'clearance_ledger.json').read_text()):
            validator.validate(c);d=docs[held[c['original_candidate_id']]['document_id']];t=(OLD/d['text_path']).read_text()
            for p in c['clearances']:self.assertEqual(t[p['proof_start']:p['proof_end']],p['proof_text'])
            self.assertFalse(c['annotation_transferred']);self.assertFalse(c['training_approved'])
    def test_return_validator_recognizes_supplement_and_rejects_tampering(self):
        with (PACKET/'orbit-development-review.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        _,baseline=select_baseline(rows);self.assertFalse(audit_return(rows,baseline)['fatal_conflicts']);rows[0]['event_id']='changed';self.assertTrue(audit_return(rows,baseline)['fatal_conflicts'])

if __name__=='__main__':unittest.main()
