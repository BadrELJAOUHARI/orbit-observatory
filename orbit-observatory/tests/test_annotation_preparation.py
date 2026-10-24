"""Synthetic annotation tasks only; no simulated independent human judgments."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from orbit_data.annotations import read_rows, task, validate_rows, write_rows
from orbit_data.validation import ROOT, digest, validate_record


def synthetic_task():
    text = "Synthetic prior context.\nCafé, sovereign borders: synthetic evidence only.\nSynthetic later context."
    start = text.index("Café")
    end = text.index("\n", start)
    doc = dict(id="synthetic-doc", actor_id="EU", language="fr", text_sha256=digest(text.encode()),
               issuer="Synthetic institution", canonical_url="https://example.org/synthetic",
               resolved_url="https://example.org/synthetic.pdf")
    event = dict(id="synthetic-event", event_date="2023-09-21")
    claim = dict(id="synthetic-candidate", lens_id="territorial_recognition", start=start, end=end)
    return task(doc, event, claim, text, "B01", []), text


class AnnotationPreparationTests(unittest.TestCase):
    def test_exact_unicode_passage_context_and_blank_human_fields(self):
        row, text = synthetic_task()
        self.assertEqual(text[row["start"]:row["end"]], row["exact_passage"])
        self.assertEqual(text[row["context_start"]:row["context_end"]], row["context_before"] + row["exact_passage"] + row["context_after"])
        self.assertEqual([row[k] for k in ["label", "annotator_id", "review_status", "review_notes"]], [""] * 4)
        self.assertTrue(row["language_review_required"])
        validate_rows([row], [row])

    def test_csv_jsonl_roundtrip_and_multiline_quotes(self):
        row, _ = synthetic_task()
        row["review_notes"] = 'Synthetic note with "quotes", comma and\na newline'
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "synthetic"
            write_rows(stem, [row])
            for suffix in [".csv", ".jsonl"]:
                self.assertEqual(read_rows(stem.with_suffix(suffix)), [row])

    def test_reference_offset_passage_and_event_tampering_rejected(self):
        expected, _ = synthetic_task()
        for key, value in [("start", 0), ("event_id", "invented-event"), ("exact_passage", "changed text"), ("text_sha256", "0" * 64)]:
            row = dict(expected)
            row[key] = value
            with self.assertRaises(ValueError):
                validate_rows([row], [expected])

    def test_duplicate_missing_and_invented_candidates_rejected(self):
        row, _ = synthetic_task()
        for rows in [[row, row], [], [dict(row, candidate_id="invented")]]:
            with self.assertRaises(ValueError):
                validate_rows(rows, [row])

    def test_labels_require_identity_and_substantive_notes(self):
        expected, _ = synthetic_task()
        row = dict(expected, label="mixed", review_status="needs_adjudication")
        with self.assertRaises(ValueError): validate_rows([row], [expected])
        row["annotator_id"] = "synthetic-test-identity"
        with self.assertRaises(ValueError): validate_rows([row], [expected])
        row["review_notes"] = "Synthetic conflicting claims require splitting."
        validate_rows([row], [expected])
        with self.assertRaises(ValueError): validate_rows([row], [expected], completed=True)

    def test_language_deferral_is_not_substantive_unresolved(self):
        expected, _ = synthetic_task()
        row = dict(expected, review_status="needs_language_review", review_notes="Synthetic language-skill deferral")
        validate_rows([row], [expected])
        row["label"] = "unresolved"
        with self.assertRaises(ValueError): validate_rows([row], [expected])

    def test_unknown_machine_label_fields_rejected(self):
        row, _ = synthetic_task()
        changed = dict(row, model_suggested_label="support")
        with self.assertRaises(ValidationError): validate_rows([changed], [row])

    def test_human_work_never_overwritten(self):
        row, _ = synthetic_task()
        edited = dict(row, review_notes="Synthetic partial human work")
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "synthetic"
            write_rows(stem, [edited])
            before = stem.with_suffix(".csv").read_bytes()
            with self.assertRaises(ValueError): write_rows(stem, [row])
            self.assertEqual(before, stem.with_suffix(".csv").read_bytes())

    def test_new_mixed_annotation_schema_preserves_old_version(self):
        annotation = dict(schema_version="1.1.0", record_type="annotation", id="synthetic-annotation",
                          claim_id="synthetic-claim", origin="human", annotator_id="synthetic-test-identity",
                          codebook_version="1.0.0", label="mixed", review_status="unreviewed",
                          created_at="2026-10-23T12:00:00Z", rationale="Synthetic conflicting clauses", supersedes=None)
        validate_record(annotation)
        old = dict(annotation, schema_version="1.0.0")
        with self.assertRaises(ValidationError): validate_record(old)
        annotation["origin"] = "model"
        with self.assertRaises(ValidationError): validate_record(annotation)

    def test_five_codebooks_match_frozen_targets_and_applicability(self):
        book = json.loads((ROOT / "codebooks/v1.0.0/codebooks.json").read_text())
        from orbit_data.validation import load_config
        _, lenses = load_config()
        self.assertEqual(len(book["lenses"]), 5)
        for lens in book["lenses"]:
            for key in ["definition", "applicable_from", "applicable_until"]:
                self.assertEqual(lens[key], lenses[lens["id"]][key])
            self.assertTrue(all(label in lens["rules"] for label in ["support", "oppose", "no_stance", "mixed", "unresolved"]))


if __name__ == "__main__":
    unittest.main()
