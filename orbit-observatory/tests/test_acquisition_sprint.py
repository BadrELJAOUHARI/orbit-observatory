import csv
import json
import unittest
from orbit_data.sprint_review import extra_gates, suggest, Groups, OUT, PACKET
from orbit_data.review_import import audit_return, select_baseline
from orbit_data.validation import digest
from orbit_data.acquisition_sprint import military_recipient_is_ukraine

class AdmissionTests(unittest.TestCase):
    def row(self,p,lens='sanctions'):
        return dict(exact_passage=p,lens_id=lens,context_before='Russia invaded Ukraine.\n')
    def doc(self):return dict(source_type='treasury',new_source_document=True)
    def test_link_only_is_rejected(self):
        self.assertEqual(extra_gates(self.row('Read the full OFAC Russia sanctions fact sheet.'),self.doc())[1],'link_or_navigation_not_policy_statement')
    def test_wrong_conflict_is_held(self):
        flags,_=extra_gates(self.row('We impose sanctions on Iran and North Korea.'),self.doc())
        self.assertIn('sanctions_target_or_conflict_basis_review',flags)
    def test_future_context_does_not_supply_conflict_basis(self):
        r=self.row('These sanctions remain in force.');r['context_before']='Another unrelated item.'
        self.assertIn('Ukraine_sanctions_basis_not_local',extra_gates(r,self.doc())[0])
    def test_pdf_fragment_is_held(self):
        flags,_=extra_gates(self.row('The European Council calls on Russia to withdraw','troop_withdrawal'),dict(source_type='council',new_source_document=True))
        self.assertIn('incomplete_sentence_boundary',flags)
    def test_conditional_suggestion_not_confident_polarity(self):
        label,_=suggest(self.row('Sanctions will end only if Russia withdraws from Ukraine.'))
        self.assertEqual(label,'unresolved')
    def test_sanctions_mention_is_not_automatic_support(self):
        label,_=suggest(self.row('The imposition of crippling unilateral sanctions against Russia has been unprecedented.'))
        self.assertEqual(label,'unresolved')
        self.assertEqual(suggest(self.row('Today OFAC imposed sanctions on Russia for its invasion of Ukraine.'))[0],'support')
    def test_transitive_copy_groups(self):
        g=Groups('abcd');g.union('a','c');g.union('c','b')
        self.assertEqual(g.find('a'),g.find('b'));self.assertNotEqual(g.find('a'),g.find('d'))
    def test_military_recipient_and_humanitarian_distinction(self):
        self.assertTrue(military_recipient_is_ukraine('We continue military support to Ukraine.'))
        self.assertTrue(military_recipient_is_ukraine('We will not provide weapons to Ukraine.'))
        self.assertFalse(military_recipient_is_ukraine('Russia receives weapons from North Korea for its invasion of Ukraine.'))
        self.assertFalse(military_recipient_is_ukraine('We send humanitarian assistance to Ukraine.'))

class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads((PACKET/'review_queue.json').read_text())
        cls.refs=json.loads((PACKET/'source_refs.json').read_text())
    def test_exact_offsets_context_and_blank_human_fields(self):
        for r in self.rows:
            ref=self.refs[r['candidate_id']];text=__import__('pathlib').Path(ref['source_text_path']).read_text()
            self.assertEqual(digest(text.encode()),r['text_sha256'])
            self.assertEqual(text[int(r['start']):int(r['end'])],r['exact_passage'])
            self.assertEqual(text[int(r['context_start']):int(r['start'])],r['context_before'])
            self.assertEqual(text[int(r['end']):int(r['context_end'])],r['context_after'])
            self.assertEqual(r['event_role'],'development_only');self.assertEqual(r['quality_flags'],'')
            self.assertFalse(r['human_label']);self.assertFalse(r['human_annotator_id']);self.assertEqual(r['human_independent'],'false')
    def test_no_reserved_group_in_export(self):
        split=json.loads((OUT/'split_assignments.json').read_text())
        reserved={x['group_id'] for x in split.values() if x['role']=='evaluation_reserved'}
        self.assertFalse(reserved & {r['leakage_group_id'] for r in self.rows})
    def test_ids_unique_and_suggestions_not_approved(self):
        self.assertEqual(len({r['candidate_id'] for r in self.rows}),len(self.rows))
        suggestions=json.loads((PACKET/'ai_suggestions.json').read_text())
        self.assertTrue(all(not r['training_approved'] and not r['human_reviewed'] and r['origin']=='ai_generated_unreviewed' for r in suggestions))
    def test_return_validator_and_evidence_tampering(self):
        with (PACKET/'orbit-development-review.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        _,baseline=select_baseline(rows)
        self.assertFalse(audit_return(rows,baseline)['fatal_conflicts'])
        rows[0]['exact_passage']='tampered'
        self.assertTrue(audit_return(rows,baseline)['fatal_conflicts'])

if __name__=='__main__':unittest.main()
