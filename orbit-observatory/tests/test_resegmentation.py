"""Synthetic fixtures for line reconstruction, alignment, lineage and safe reuse."""
import tempfile
import unittest
from pathlib import Path
from jsonschema import ValidationError
from orbit_data.resegment import source_lines, units, sentence_windows, actor_attribution, validate_transfers, layout_header_line, validate_export_references
from orbit_data.annotations import task
from orbit_data.validation import validate_dataset, validate_record
from orbit_data.collect import build_records
from test_data_pipeline import fixture_manifest, SyntheticDownloader


def v2_claim(parent,text):
    return dict(parent,schema_version='2.0.0',id='synthetic-v2',selection_method='source_aligned_sentences_v2',
                reading_text=parent['quote'].replace('\n',' '),source_indices=list(range(parent['start'],parent['end'])),
                segment_kind='sentence',derived_from=[parent['id']],quality_issues=[],paragraph_id='synthetic-paragraph',
                segmentation_version='orbit-segmentation-2.0.0')


class ResegmentationTests(unittest.TestCase):
    def test_header_prefix_does_not_delete_body_text(self):
        self.assertFalse(layout_header_line('UN General Assembly. They follow closely developments at the'))
        self.assertTrue(layout_header_line('UN GENERAL ASSEMBLY 13.00'))
        text='Synthetic opening continues at the\nUN General Assembly. Next sentence.'
        found,_,_=units(text,source_lines(text))
        self.assertIn('UN General Assembly.',found[0]['reading_text'])

    def test_front_matter_separate_from_body(self):
        text='SYNTHETIC TITLE\n1\nSynthetic body begins\nand continues.'
        found,_,omitted=units(text,source_lines(text),body_start=text.index('Synthetic body'))
        self.assertEqual(found[0]['reading_text'],'Synthetic body begins and continues.')
        self.assertEqual([o['reason'] for o in omitted],['front_matter_or_salutation']*2)

    def test_unit_pages_describe_sentence_rather_than_whole_paragraph(self):
        text='Synthetic first sentence.\nSynthetic second sentence.'
        lines=source_lines(text)
        for i,line in enumerate(lines):
            line.update(page=i+1,blank_before=False)
        found,blocks,_=units(text,lines)
        self.assertEqual(blocks[0]['pages'],[1,2])
        self.assertEqual([u['pages'] for u in found],[[1],[2]])

    def test_multiline_sentence_is_one_exact_mapped_unit(self):
        text='Synthetic Ukraine sentence\ncontinues in French café. Next sentence.'
        found,_,_=units(text,source_lines(text))
        self.assertEqual(len(found),2)
        self.assertEqual(found[0]['reading_text'],'Synthetic Ukraine sentence continues in French café.')
        for u in found:
            self.assertEqual(u['reading_text'],''.join(text[i].replace('\n',' ') for i in u['source_indices']))
            self.assertEqual(text[u['start']:u['end']].replace('\n',' '),u['reading_text'])

    def test_page_headers_do_not_cut_sentence_and_raw_envelope_survives(self):
        text='Synthetic sentence continues\nV7\n78TH UN GENERAL ASSEMBLY DEBATE\n19 SEPTEMBER 2023\nNEW YORK, USA\n2\nacross this page. Next one.'
        lines=source_lines(text)
        for line in lines:line['page']=1 if line['start']==0 else 2
        found,blocks,omitted=units(text,lines)
        self.assertEqual(found[0]['reading_text'],'Synthetic sentence continues across this page.')
        self.assertIn('V7',text[found[0]['start']:found[0]['end']])
        self.assertEqual(len(omitted),5)
        self.assertEqual(len(blocks),1)
        self.assertEqual(blocks[0]['pages'],[1,2])

    def test_blank_or_geometry_cannot_cut_incomplete_sentence(self):
        text='Synthetic incomplete\ncontinued sentence.\nAnother paragraph.'
        lines=source_lines(text)
        for line in lines:line['geometry_paragraph_before']=True
        found,blocks,_=units(text,lines)
        self.assertEqual(len(blocks),2)
        self.assertEqual(found[0]['reading_text'],'Synthetic incomplete continued sentence.')

    def test_french_quotation_titles_initials_and_decimal(self):
        text='M. Michel dit « Ceci continue. » La suite est française. Dr. S. Test cites 1. 3 billion.'
        parts=[text[a:b] for a,b in sentence_windows(text)]
        self.assertEqual(parts,['M. Michel dit « Ceci continue. »','La suite est française.','Dr. S. Test cites 1. 3 billion.'])

    def test_speaker_turns_never_merge(self):
        text='PRESIDENT OBAMA: Synthetic US sentence.\nPRIME MINISTER YATSENYUK: Synthetic Ukrainian sentence.\nQ Synthetic question?\nTHE PRESIDENT: Synthetic answer.'
        found,_,_=units(text,source_lines(text),True)
        self.assertEqual(len(found),4)
        issues=[actor_attribution({'actor_id':'USA'},u['speaker'])[1] for u in found]
        self.assertEqual(issues,[[],['attribution_actor_mismatch'],['attribution_actor_mismatch'],[]])
        self.assertTrue(all('label' not in u for u in found))

    def test_v2_offsets_and_lineage_reject_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            records=build_records(fixture_manifest(),output,SyntheticDownloader(output))[0]
            parent=next(r for r in records if r['record_type']=='claim')
            doc=next(r for r in records if r['record_type']=='document')
            text=(output/doc['text_path']).read_text()
            child=v2_claim(parent,text)
            validate_dataset(records+[child],output)
            for changed in [dict(child,reading_text=child['reading_text']+'X'),dict(child,source_indices=child['source_indices'][1:]),dict(child,derived_from=['unknown'])]:
                with self.assertRaises((ValueError,KeyError)):validate_dataset(records+[changed],output)
            with self.assertRaises(ValueError):validate_dataset(records+[child,dict(child,id='another-synthetic-id')],output)
            with self.assertRaises(ValidationError):validate_record(dict(child,quality_issues=['model_ambiguity']))

    def test_export_context_and_source_references_checked_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            records=build_records(fixture_manifest(),output,SyntheticDownloader(output))[0]
            claim=next(r for r in records if r['record_type']=='claim')
            doc=next(r for r in records if r['record_type']=='document')
            event=next(r for r in records if r['record_type']=='event')
            text=(output/doc['text_path']).read_text()
            row=task(doc,event,claim,text,'SYNTHETIC',[])
            validate_export_references([row],records,{doc['id']:text})
            for changed in [dict(row,context_after='Invented context'),dict(row,source_url='https://example.org/wrong'),dict(row,event_date='2023-01-01')]:
                with self.assertRaises(ValueError):validate_export_references([changed],records,{doc['id']:text})

    def test_transfer_requires_unchanged_evidence_speaker_and_no_new_vote(self):
        p=dict(record_type='claim',id='parent',document_id='doc',event_id='event',lens_id='sanctions',text_sha256='a'*64,start=0,end=4,quote='Text',speaker='Synthetic speaker')
        c=dict(p,id='child',quality_issues=['scope_insufficiency'])
        a=dict(record_type='annotation',id='annotation',claim_id='parent',scoring_status='held')
        t=dict(transfer_version='1.0.0',transfer_id='transfer',from_annotation_id='annotation',from_candidate_id='parent',to_candidate_id='child',source_text_sha256='a'*64,basis='identical_source_envelope_event_lens_context_and_speaker_turn',source_speaker='Synthetic speaker',ai_assisted=True,independent_human=False,new_independent_judgment=False,scoring_status='held',retained_quality_issues=['scope_insufficiency'])
        validate_transfers([t],[p,c,a])
        for changed in [dict(c,quote='Changed'),dict(c,speaker='Different speaker'),dict(c,quality_issues=[])]:
            with self.assertRaises(ValueError):validate_transfers([t],[p,changed,a])
        with self.assertRaises(ValidationError):validate_transfers([dict(t,independent_human=True)],[p,c,a])
        with self.assertRaises(ValueError):validate_transfers([t,t],[p,c,a])
        with self.assertRaises(ValueError):validate_transfers([dict(t,scoring_status='eligible')],[p,c,a])

if __name__=='__main__': unittest.main()
