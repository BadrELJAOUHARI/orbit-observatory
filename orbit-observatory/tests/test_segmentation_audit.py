"""Boundary screens use synthetic fixtures and never change source/labels."""

import copy
import tempfile
import unittest
from pathlib import Path

from orbit_data.followup import WINDOWS, expand
from orbit_data.segmentation import audit_boundaries, boundary_flags, terminal
from orbit_data.validation import digest


class SegmentationAuditTests(unittest.TestCase):
    def test_pdf_line_is_flagged_at_both_incomplete_edges(self):
        text = "Synthetic sentence begins here and\ncontinues with synthetic evidence and\nends here."
        start = text.index("continues")
        end = text.index("\n", start)
        flags, _ = boundary_flags(text, start, end)
        self.assertIn("possible_missing_sentence_start", flags)
        self.assertIn("possible_missing_sentence_end", flags)

    def test_complete_multiline_span_is_not_penalized_for_linebreaks(self):
        text = "Previous sentence.\nA complete synthetic\nsentence finishes here.\nAnother sentence."
        start = text.index("A complete")
        end = text.index("\nAnother")
        self.assertEqual(boundary_flags(text, start, end)[0], [])

    def test_headers_and_abbreviations_are_handled_conservatively(self):
        self.assertFalse(terminal("Addressed to Mr."))
        text = "Previous complete sentence.\n4\nA complete synthetic sentence."
        start = text.index("A complete")
        flags, skipped = boundary_flags(text, start, len(text))
        self.assertEqual(flags, [])
        self.assertEqual(skipped, 1)

    def test_audit_is_flag_only_and_preserves_records(self):
        text = "Synthetic earlier\nsynthetic candidate\nfinishes later."
        start = text.index("synthetic candidate")
        end = text.index("\n", start)
        records = [dict(record_type="document", id="synthetic-doc", actor_id="EU", language="en", text_path="synthetic.txt"),
                   dict(record_type="claim", id="synthetic-claim", document_id="synthetic-doc", event_id="synthetic-event", text_sha256=digest(text.encode()), start=start, end=end, quote=text[start:end])]
        before = copy.deepcopy(records)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "synthetic.txt").write_text(text)
            report = audit_boundaries(records, Path(tmp))
        self.assertEqual(records, before)
        self.assertEqual(report["counts"]["original_candidate"]["flagged"], 1)
        self.assertFalse(report["findings"][0]["stance_label_assigned"])
        self.assertNotIn("label", report["findings"][0])

    def test_all_requested_repairs_preserve_parent_and_source_indices(self):
        for row_id, (begin, ending) in WINDOWS.items():
            text = "Synthetic before. " + begin + "\nSYNTHETIC CENTRAL FIXTURE\n" + ending + "\nSynthetic after."
            start = text.index("SYNTHETIC CENTRAL")
            end = text.index("\n", start)
            parent = dict(id="synthetic-" + row_id, start=start, end=end, quote=text[start:end], text_sha256=digest(text.encode()))
            before = dict(parent)
            revised = expand(parent, text, row_id, "2026-10-23T12:00:00Z", "synthetic-reviewer")
            self.assertEqual(parent, before)
            self.assertEqual(revised["quote"], text[revised["start"]:revised["end"]])
            self.assertEqual(revised["revision_of"], parent["id"])
            self.assertNotIn("label", revised)


if __name__ == "__main__":
    unittest.main()
