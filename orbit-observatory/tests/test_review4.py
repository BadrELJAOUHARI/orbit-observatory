"""Synthetic review metadata, control lineage and current-family counting checks."""
import copy
import unittest
from jsonschema import ValidationError
from orbit_data.review4 import validate_quality, repair_control, family_summary
from orbit_data.resegment import source_lines, units
from orbit_data.validation import load_config


class Review4Tests(unittest.TestCase):
    def quality_fixture(self):
        doc=dict(id='doc',record_type='document',language='fr')
        claim=dict(id='claim',record_type='claim',document_id='doc',text_sha256='a'*64,
                   quality_issues=['EU_common_position_review','language_review'])
        annotation=dict(id='annotation',record_type='annotation',claim_id='claim',batch_id='V2-B02')
        assessment=dict(schema_version='1.0.0',record_type='review_quality_assessment',assessment_id='quality',annotation_id='annotation',
            candidate_id='claim',review_id='synthetic',scope_reason='Synthetic scope pending',source_eligibility_flags=['EU_common_position_review','language_review'],
            evidence_quality_flags=[],scope_flags=[],directional_scoring_eligible=False,
            language_review='assisted_French_review_not_independent_language_validation',source_text_sha256='a'*64)
        return [doc,claim,annotation],assessment

    def test_assisted_language_review_cannot_clear_source_flags(self):
        records,assessment=self.quality_fixture()
        validate_quality([assessment],records)
        with self.assertRaises(ValueError):
            validate_quality([dict(assessment,source_eligibility_flags=['language_review'])],records)
        with self.assertRaises(ValidationError):
            validate_quality([dict(assessment,directional_scoring_eligible=True)],records)
        changed=copy.deepcopy(records)
        changed[0]['language']='en'
        with self.assertRaises(ValueError):validate_quality([assessment],changed)

    def test_scope_exclusion_and_annotation_reference_checked(self):
        records,assessment=self.quality_fixture()
        records[-1]['batch_id']='V2-B05'
        with self.assertRaises(ValueError):validate_quality([assessment],records)
        validate_quality([dict(assessment,scope_flags=['scope_insufficiency'])],records)
        records[-1]['claim_id']='another'
        with self.assertRaises(ValueError):validate_quality([dict(assessment,scope_flags=['scope_insufficiency'])],records)

    def test_control_repair_retains_sample_instead_of_resampling(self):
        text='Synthetic previous sentence.\nSynthetic selected sentence begins here and\ncontinues on this physical line.\nSynthetic following sentence.'
        start=text.index('continues')
        original=dict(candidate_id='synthetic-control',start=start,end=text.index('\n',start),lens_id='sanctions')
        before=copy.deepcopy(original)
        us,blocks,omitted=units(text,source_lines(text))
        doc=dict(id='doc',actor_id='EU',language='en',text_sha256='a'*64,translation_provenance=None)
        _,lenses=load_config()
        repaired=repair_control(original,doc,dict(id='event'),text,dict(units=us,omitted=omitted),lenses)
        self.assertEqual(original,before)
        self.assertLess(repaired['start'],original['start'])
        self.assertEqual(repaired['end'],original['end'])
        self.assertEqual(repaired['quote'],text[repaired['start']:repaired['end']])
        self.assertNotIn('label',repaired)
        self.assertIn('EU_common_position_review',repaired['quality_issues'])
        self.assertEqual(repaired,repair_control(original,doc,dict(id='event'),text,dict(units=us,omitted=omitted),lenses))

    def test_revisions_and_transfer_aliases_do_not_inflate_current_counts(self):
        claims=[dict(id='root',record_type='claim'),dict(id='revision',record_type='claim',revision_of='root'),dict(id='v2',record_type='claim')]
        annotations=[dict(id='a1',record_type='annotation',claim_id='root',batch_id='SYNTHETIC',label='unresolved',review_notes='Synthetic defective span.'),
                     dict(id='a2',record_type='annotation',claim_id='revision',batch_id='SYNTHETIC-R1',label='support',review_notes='Synthetic repaired judgment.'),
                     dict(id='a3',record_type='annotation',claim_id='v2',batch_id='SYNTHETIC-V2',label='support',review_notes='Synthetic exact alias.')]
        for n,batch in enumerate(['B09-R1','B10-R1','V2-B05']):
            claims.append(dict(id=f'scope-{n}',record_type='claim'))
            annotations.append(dict(id=f'scope-ann-{n}',record_type='annotation',claim_id=f'scope-{n}',batch_id=batch,label='unresolved',review_notes='Synthetic scope insufficiency fixture.'))
        summary=family_summary(claims+annotations,[dict(to_candidate_id='v2',from_candidate_id='revision')],[])
        self.assertEqual(summary['historical_decisions'],6)
        self.assertEqual(summary['current_review_families'],4)
        self.assertEqual(summary['current_label_counts'],{'support':1,'unresolved':3})
        self.assertEqual(summary['independent_annotations'],0)

if __name__=='__main__':unittest.main()
