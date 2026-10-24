"""Synthetic fixtures for hierarchy, split leakage, quarantine and blind exports."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from jsonschema import ValidationError
from orbit_data.aggregation import aggregate
from orbit_data.workflow import screen,priority,render_html,SUGGESTION_VALIDATOR
from orbit_data.training import eligible_training_rows,assert_training_ready,train_baseline
from orbit_data.review_import import validate_return


def fixture(event,day,p=.75,key='same',claim=None):
    return dict(origin='test_fixture',actor_id='TEST',lens_id='TEST_LENS',stream='TEST_ONLY',
        event_id=event,event_date=day,claim_id=claim or event+'-claim',canonical_claim_key=key,support_probability=p)


class HierarchyTests(unittest.TestCase):
    def test_equal_claim_event_and_quarter_weights_not_document_mean(self):
        rows=[fixture('A','2024-01-01',1,key='one'),fixture('A','2024-01-01',0,key='two',claim='other'),
              fixture('B','2024-02-01',1),fixture('C','2024-04-01',0)]
        result=aggregate(rows,'TEST','TEST_LENS',2024,'TEST_ONLY',allow_fixtures=True)
        self.assertEqual(result['provisional_observed_window_score'],-.25)
        self.assertIsNone(result['annual_score'])
        self.assertAlmostEqual(sum(r['claim_weight'] for r in result['ledger']),1)
        self.assertAlmostEqual(sum(r['contribution'] for r in result['ledger']),-.25)
        self.assertFalse(result['publishable'])

    def test_duplicate_mirror_or_translation_does_not_buy_weight(self):
        a=fixture('A','2024-01-01',1)
        rows=[a,dict(a,claim_id='mirror'),fixture('B','2024-02-01',0)]
        result=aggregate(rows,'TEST','TEST_LENS',2024,'TEST_ONLY',allow_fixtures=True)
        self.assertEqual(len(result['ledger']),2)
        self.assertEqual(result['provisional_observed_window_score'],0)
        with self.assertRaises(ValueError):aggregate([a,dict(a,support_probability=0)],'TEST','TEST_LENS',2024,'TEST_ONLY',allow_fixtures=True)

    def test_coverage_requires_distinct_dates_in_all_four_quarters(self):
        rows=[fixture(f'{q}-{day}',f'2024-{q*3-2:02}-{day:02}') for q in range(1,5) for day in (1,2)]
        result=aggregate(rows,'TEST','TEST_LENS',2024,'TEST_ONLY',allow_fixtures=True)
        self.assertTrue(result['annual_coverage_gate_passed'])
        self.assertEqual(result['effective_event_count'],8)
        self.assertEqual(result['annual_score'],.5)
        self.assertFalse(result['publishable'])
        rows[1]['event_date']=rows[0]['event_date']
        self.assertFalse(aggregate(rows,'TEST','TEST_LENS',2024,'TEST_ONLY',allow_fixtures=True)['annual_coverage_gate_passed'])

    def test_empty_is_null_ai_drafts_and_unmarked_fixtures_rejected(self):
        self.assertIsNone(aggregate([],'TEST','TEST_LENS',2024,'TEST_ONLY')['annual_score'])
        for row in [fixture('A','2024-01-01'),dict(fixture('A','2024-01-01'),origin='ai_generated')]:
            with self.assertRaises(ValueError):aggregate([row],'TEST','TEST_LENS',2024,'TEST_ONLY')
        with self.assertRaises(ValueError):aggregate([fixture('A','2023-01-01')],'TEST','TEST_LENS',2024,'TEST_ONLY',allow_fixtures=True)


class ConsolidationTests(unittest.TestCase):
    def test_header_resolution_preserves_frozen_quote_and_flags(self):
        text='Synthetic starts\n2\ncontinues.'
        indices=list(range(16))+list(range(18,len(text)))
        # Build the actual map explicitly, leaving the page marker and its LF out.
        indices=list(range(text.index('2')))+list(range(text.index('continues'),len(text)))
        c=dict(id='synthetic',start=0,end=len(text),source_indices=indices,
               reading_text=''.join(' ' if text[i]=='\n' else text[i] for i in indices),
               quality_issues=['extraction_header_in_envelope'])
        before=copy.deepcopy(c)
        result=screen(c,dict(context_start=0,context_end=len(text)),text)
        self.assertFalse(result['quarantine'])
        self.assertTrue(result['mechanical_resolutions'])
        self.assertEqual(c,before)
        c['quality_issues'].append('EU_common_position_review')
        self.assertTrue(screen(c,dict(context_start=0,context_end=len(text)),text)['quarantine'])

    def test_uncertain_word_spacing_is_quarantined_not_guessed(self):
        text='Synthetic Ukraine conflict continue s here.'
        c=dict(id='synthetic',quality_issues=[])
        result=screen(c,dict(context_start=0,context_end=len(text)),text)
        self.assertTrue(result['quarantine'])
        self.assertEqual(text[result['suspect_source_spans'][0]['start']:result['suspect_source_spans'][0]['end']],'continue s')
        self.assertFalse(result['scoring_eligible'])

    def test_opposition_mixed_scope_and_source_problems_get_priority(self):
        base=dict(quarantine=False,effective_flags=[])
        self.assertGreater(priority(base,dict(label='mixed',review_flags=[]),None)[0],priority(base,dict(label='no_stance',review_flags=[]),None)[0])
        self.assertEqual(priority(dict(base,quarantine=True),None,None)[0],100)
        self.assertEqual(priority(dict(base,effective_flags=['scope_insufficiency']),None,None)[0],95)

    def test_draft_suggestion_cannot_claim_human_review_or_probability(self):
        example=dict(suggestion_version='1.0.0',record_type='ai_suggestion',id='synthetic-draft',candidate_id='synthetic',
            event_id='synthetic-event',label='support',rationale='Synthetic rationale only.',review_flags=[],origin='ai_generated',
            review_status='unreviewed',annotator_id=None,independent_human=False,model_probability=None,calibrated=False,
            scoring_eligible=False,training_approved=False,method='synthetic-test',input_snapshot_sha256='a'*64,
            evidence_context_sha256='b'*64,evaluation_sealed=False)
        SUGGESTION_VALIDATOR.validate(example)
        for changed in [dict(example,annotator_id='Badr_A'),dict(example,review_status='reviewed'),dict(example,model_probability=.99)]:
            with self.assertRaises(ValidationError):SUGGESTION_VALIDATOR.validate(changed)

    def test_return_cannot_mutate_evidence_or_invent_independence(self):
        baseline=dict(candidate_id='SYNTHETIC',event_role='development_only',exact_passage='Synthetic evidence.',
            human_label='',human_annotator_id='',human_review_notes='',human_independent='false')
        row=dict(baseline,human_label='support',human_annotator_id='SYNTHETIC_TEST_ONLY',human_review_notes='Synthetic reasoning.')
        self.assertEqual(len(validate_return([row],[baseline])),1)
        for changed in [dict(row,exact_passage='changed'),dict(row,human_independent='true')]:
            with self.assertRaises(ValueError):validate_return([changed],[baseline])
        with self.assertRaises(ValueError):validate_return([row],[dict(baseline,event_role='evaluation_rehearsal')])


    def test_quality_only_return_is_separate_from_stance_and_csv_bools_are_stable(self):
        from orbit_data.workflow import QUALITY_RESPONSE_OPTIONS,csv_cell
        baseline=dict(candidate_id='SYNTHETIC',event_role='development_only',language_review_required=True,
            human_label='',human_annotator_id='',human_review_notes='',human_independent='false',
            **{field:'' for field in QUALITY_RESPONSE_OPTIONS})
        row={k:csv_cell(v) for k,v in baseline.items()}
        row.update(human_source_eligibility='needs_review',human_annotator_id='SYNTHETIC_ONLY',human_review_notes='Synthetic source check, no stance judgment.')
        reviewed=validate_return([row],[baseline])
        self.assertEqual(reviewed[0]['human_label'],'')
        self.assertEqual(reviewed[0]['language_review_required'],'true')
        with self.assertRaises(ValueError):validate_return([dict(row,human_source_eligibility='automatically_publish')],[baseline])


class TrainingGuardsTests(unittest.TestCase):
    def test_ai_and_eval_events_cannot_enter_train_or_tuning(self):
        split=dict(excluded_from_training_and_tuning_event_ids=['HELD'])
        rows=[dict(event_id='DEV',origin='ai_generated'),dict(event_id='HELD',origin='human',training_approved=True)]
        good,rejected=eligible_training_rows(rows,split)
        self.assertEqual(good,[])
        self.assertEqual(sum(rejected.values()),2)
        valid=dict(event_id='DEV',origin='human',review_status='independent',training_approved=True,
                   source_eligibility_cleared=True,text_quality_cleared=True,label='support')
        prepared=dict(train=[valid,dict(valid,event_id='DEV2',label='oppose')],validation=[dict(valid,event_id='HELD')],heldout_event_ids=['HELD'])
        with self.assertRaises(ValueError):assert_training_ready(prepared)
        prepared['validation']=[dict(valid,event_id='TUNE')]
        assert_training_ready(prepared)
        prepared['train'][0]['origin']='ai_generated'
        with self.assertRaises(ValueError):assert_training_ready(prepared)
        with self.assertRaises(ValueError):train_baseline(dict(train=[],validation=[],heldout_event_ids=[]))

if __name__=='__main__':unittest.main()
