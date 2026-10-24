"""Synthetic development/evaluation separation and return compatibility tests."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from orbit_data.development_review import development_rows,render
from orbit_data.review_import import select_baseline
from orbit_data.validation import digest
from test_annotation_preparation import synthetic_task


class DevelopmentReviewTests(unittest.TestCase):
    def test_filter_excludes_evaluation_passages_and_context_without_changing_ids(self):
        row,_=synthetic_task()
        row.update(event_role='development_only',quarantine='false',quality_flags='',reading_text=row['exact_passage'],source_qualification='Synthetic source only.',
                   existing_annotation_id='synthetic-prior',existing_label='no_stance',existing_provenance='Synthetic AI-assisted prior record.',
                   existing_review_notes='Synthetic prior reasoning.',ai_suggested_label='',ai_rationale='',ai_review_flags='',human_independent='false')
        before=copy.deepcopy(row)
        evaluation=dict(row,candidate_id='eval',row_id='eval-row',event_id='eval-event',event_role='evaluation_rehearsal',exact_passage='EVALUATION_PASSAGE_DO_NOT_EMBED',context_before='EVALUATION_CONTEXT_DO_NOT_EMBED')
        split=dict(event_roles={row['event_id']:'development_only','eval-event':'evaluation_rehearsal'},reserved_event_ids=['eval-event'])
        selected=development_rows([row,evaluation],split)
        self.assertEqual(selected,[before])
        self.assertEqual(row,before)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'review.html';render(path,selected,'synthetic-packet')
            text=path.read_text()
            self.assertNotIn('EVALUATION_PASSAGE_DO_NOT_EMBED',text)
            self.assertNotIn('EVALUATION_CONTEXT_DO_NOT_EMBED',text)
            payload=json.loads(re.search(r'id="packet-data">(.*?)</script>',text,re.S).group(1))
            self.assertEqual(payload['rows'][0]['candidate_id'],row['candidate_id'])
            self.assertEqual(payload['rows'][0]['existing_provenance'],row['existing_provenance'])

    def test_reserved_event_cannot_be_mislabeled_development(self):
        row=dict(event_role='development_only',candidate_id='synthetic',row_id='R1',event_id='HELD',human_independent='false')
        with self.assertRaises(ValueError):development_rows([row],dict(event_roles={'HELD':'evaluation_rehearsal'},reserved_event_ids=['HELD']))
        with self.assertRaises(ValueError):development_rows([row,row],dict(event_roles={'HELD':'development_only'},reserved_event_ids=[]))

    def test_csv_import_auto_detects_hash_protected_development_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'app';root.mkdir()
            packet=root.parent/'.local/development-review-v2';packet.mkdir(parents=True)
            baseline=[dict(candidate_id='synthetic',event_role='development_only')]
            (packet/'review_queue.json').write_text(json.dumps(baseline))
            (packet/'manifest.json').write_text(json.dumps(dict(files={'review_queue.json':digest((packet/'review_queue.json').read_bytes())})))
            with patch('orbit_data.review_import.ROOT',root):
                path,actual=select_baseline([dict(candidate_id='synthetic')])
                self.assertEqual(actual,baseline)
                self.assertEqual(path,packet/'review_queue.json')
                (packet/'review_queue.json').write_text('[]')
                with self.assertRaises(ValueError):select_baseline([dict(candidate_id='synthetic')])

if __name__=='__main__':unittest.main()
