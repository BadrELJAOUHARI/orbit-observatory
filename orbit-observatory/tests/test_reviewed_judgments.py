"""Synthetic provenance, span-history and speaker-screen checks."""

import copy
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from orbit_data.reviewed import audit_speakers, repair_b05, write_immutable
from orbit_data.validation import digest, validate_record


class ReviewedJudgmentTests(unittest.TestCase):
    def test_assisted_review_cannot_be_recorded_as_independent(self):
        annotation = dict(schema_version="1.2.0", record_type="annotation", id="synthetic-annotation",
                          claim_id="synthetic-claim", batch_id="synthetic-batch", origin="ai_assisted_reviewed",
                          annotator_id="synthetic-reviewer", codebook_version="1.0.0", label="no_stance",
                          review_status="reviewed_non_independent", created_at="2026-10-23T12:00:00Z",
                          rationale="Synthetic reasoning", review_notes="Synthetic reasoning", supersedes=None,
                          review_provenance="Synthetic AI-assisted judgment reviewed by a user, not independent.",
                          ai_assisted=True, independent_human=False, scoring_status="excluded_actor_mismatch")
        validate_record(annotation)
        for key, value in [("independent_human", True), ("review_status", "independent"), ("origin", "model")]:
            changed = dict(annotation)
            changed[key] = value
            with self.assertRaises(ValidationError): validate_record(changed)
        with self.assertRaises(ValueError): validate_record(dict(annotation, review_notes="Changed reasoning"))

    def test_span_expansion_preserves_parent_and_stays_unlabeled(self):
        text = ("Synthetic context. In fact, there is a simple\n"
                "solution to end this food crisis that threatens us: that Russia stops the war, withdraws\n"
                "from Ukrainian territory and lifts the blockade of ports.\nSynthetic after.")
        start = text.index("solution")
        end = text.index("\n", start)
        parent = dict(id="synthetic-parent", text_sha256=digest(text.encode()), start=start, end=end, quote=text[start:end])
        before = copy.deepcopy(parent)
        revision = repair_b05(parent, text, "2026-10-23T12:00:00Z", "synthetic-reviewer")
        self.assertEqual(parent, before)
        self.assertNotEqual(revision["id"], parent["id"])
        self.assertEqual(revision["revision_of"], parent["id"])
        self.assertEqual(revision["quote"], text[revision["start"]:revision["end"]])
        self.assertTrue(revision["quote"].startswith("In fact"))
        self.assertTrue(revision["quote"].endswith("ports."))
        self.assertNotIn("label", revision)

    def test_speaker_flags_are_not_stance_labels(self):
        text = "PRESIDENT OBAMA: Synthetic US words.\nPRIME MINISTER YATSENYUK: Synthetic Ukrainian words.\nQ Synthetic reporter question.\nPRESIDENT OBAMA: Synthetic answer."
        doc = dict(record_type="document", id="synthetic-doc", actor_id="USA", text_path="synthetic.txt")
        claims = []
        for number, substring in enumerate(["Synthetic US words.", "Synthetic Ukrainian words.", "Synthetic reporter question."]):
            start = text.index(substring)
            claims.append(dict(record_type="claim", id=f"synthetic-{number}", document_id=doc["id"], event_id="synthetic-event", start=start, end=start + len(substring)))
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "synthetic.txt").write_text(text)
            result = audit_speakers([doc] + claims, cache, [])
        self.assertEqual(result["counts"]["actor_mismatch_review_required"], 2)
        self.assertEqual(result["counts"]["no_marker_mismatch_detected"], 1)
        self.assertTrue(all(not row["stance_label_assigned_by_audit"] and "label" not in row for row in result["findings"]))

    def test_immutable_review_history_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            write_immutable(path, {"review_notes": "Original synthetic reasoning"})
            before = path.read_bytes()
            write_immutable(path, {"review_notes": "Original synthetic reasoning"})
            with self.assertRaises(ValueError): write_immutable(path, {"review_notes": "Changed reasoning"})
            self.assertEqual(before, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
