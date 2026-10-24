"""Record user-reviewed assisted judgments and append-only evidence revisions."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .annotations import read_rows, task, validate_rows, write_rows
from .collect import utcnow, write_json
from .validation import ROOT, digest, validate_dataset

REVISION_TASK_VALIDATOR = Draft202012Validator(
    json.loads((ROOT / "schemas/annotation-v1.1/task.schema.json").read_text()), format_checker=FormatChecker()
)


def write_immutable(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f"Preserving existing history: {path}; use a new review ID")
        return
    write_json(path, value)


def repair_b05(parent, text, timestamp, requested_by):
    start = text.index("In fact, there is a simple", max(0, parent["start"] - 100), parent["start"])
    suffix = "from Ukrainian territory and lifts the blockade of ports."
    end = text.index(suffix, parent["end"]) + len(suffix)
    if not start < parent["start"] < parent["end"] < end:
        raise ValueError("B05 expansion does not contain the original span")
    revision = dict(parent)
    revision.update(schema_version="1.1.0", id="claim-revision-" + digest(
        f"{parent['id']}:{parent['text_sha256']}:{start}:{end}".encode()),
        start=start, end=end, quote=text[start:end],
        selection_method="review_requested_span_expansion_v1", revision_of=parent["id"],
        revision_reason="Badr_A requested expansion of an incomplete PDF line to the complete stored sentence; territorial-scope and final stance review remain pending.",
        revision_requested_by=requested_by, created_at=timestamp,
        unresolved_reason="Repaired span awaiting a new reviewed judgment; do not transfer the original unresolved label or infer support.")
    return revision


def audit_speakers(records, cache, annotations):
    reviewed = {a["claim_id"]: a["id"] for a in annotations}
    docs = {r["id"]: r for r in records if r["record_type"] == "document" and r["actor_id"] == "USA"}
    findings = []
    marker_pattern = re.compile(r"(?m)^(PRESIDENT OBAMA:|PRIME MINISTER YATSENYUK:|THE PRESIDENT:|Q(?=\s))")
    for identifier, doc in docs.items():
        text = (cache / doc["text_path"]).read_text(encoding="utf-8")
        markers = list(marker_pattern.finditer(text))
        segments = []
        for index, marker in enumerate(markers):
            speaker = marker.group()
            actor = "UKR" if speaker.startswith("PRIME MINISTER") else None if speaker == "Q" else "USA"
            segments.append(dict(start=marker.start(), end=markers[index + 1].start() if index + 1 < len(markers) else len(text),
                                 marker=speaker, actor_id=actor))
        for claim in records:
            if claim["record_type"] != "claim" or claim["document_id"] != identifier:
                continue
            overlaps = [s for s in segments if claim["start"] < s["end"] and claim["end"] > s["start"]]
            mismatch = not overlaps or any(s["actor_id"] != doc["actor_id"] for s in overlaps)
            mixed = len({s["marker"] for s in overlaps}) > 1
            findings.append(dict(candidate_id=claim["id"], document_id=identifier, event_id=claim["event_id"],
                                 target_actor_id="USA", start=claim["start"], end=claim["end"],
                                 source_speaker_segments=overlaps,
                                 flag="mixed_speakers_review_required" if mixed else "actor_mismatch_review_required" if mismatch else "no_marker_mismatch_detected",
                                 scoring_gate="hold_for_attribution_review" if mismatch or mixed else "not_cleared_by_this_marker_screen",
                                 stance_label_assigned_by_audit=False,
                                 existing_reviewed_annotation_id=reviewed.get(claim["id"])))
    return dict(method="speaker-marker-screen-v1", findings=findings,
                limitations="Marker-based screening does not resolve quotations inside a speaker turn or unmarked speaker changes. Flags require review and assign no stance labels.",
                counts=dict(Counter(f["flag"] for f in findings)))


def record_review(cache, batch_directory, submission_path):
    records = json.loads((cache / "records.json").read_text())
    validate_dataset(records, cache)
    submission = json.loads(submission_path.read_text())
    if submission["ai_assisted"] is not True or submission["independent_human"] is not False:
        raise ValueError("This importer is specifically for non-independent, AI-assisted reviewed decisions")
    annotator, review_id = submission["annotator_id"], submission["submission_id"]
    if not all(re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in (annotator, review_id)):
        raise ValueError("Unsafe annotator/review identifier")
    ledger_dir = ROOT / "annotations/v1/reviews" / annotator
    ledger_path = ledger_dir / (review_id + ".review.json")
    private = batch_directory / "reviews" / annotator / review_id
    submission_sha = digest(submission_path.read_bytes())
    if ledger_path.exists():
        existing = json.loads(ledger_path.read_text())
        if existing["submission_sha256"] != submission_sha:
            raise ValueError("Changed submission cannot overwrite an existing review")
        overlay = json.loads((private / "overlay_records.json").read_text())
        prior = [a for p in sorted(ledger_dir.glob("*.review.json")) if p != ledger_path
                 for a in json.loads(p.read_text())["annotations"]]
        if [r for r in overlay if r["record_type"] == "annotation"] != existing["annotations"]:
            raise ValueError("Review ledger and private annotation overlay disagree")
        if digest((private / "B05-R1.claim.json").read_bytes()) != existing["span_revision"]["file_sha256"]:
            raise ValueError("Recorded span revision checksum changed")
        revision = json.loads((private / "B05-R1.claim.json").read_text())
        if revision not in overlay:
            raise ValueError("Span revision missing from private overlay")
        validate_dataset(records + prior + overlay, cache)
        return existing

    base = read_rows(batch_directory / "first_batch.jsonl")
    meta = json.loads((batch_directory / "manifest.json").read_text())
    if digest((batch_directory / "first_batch.jsonl").read_bytes()) != meta["artifacts"]["first_batch.jsonl"]:
        raise ValueError("Original batch no longer matches its preparation manifest")
    by_batch = {row["row_id"]: row for row in base}
    judgments = submission["judgments"]
    if len({j["batch_id"] for j in judgments}) != len(judgments):
        raise ValueError("Duplicate submitted batch ID")
    timestamp = utcnow()
    previous_ledgers = sorted(ledger_dir.glob("*.review.json"))
    prior_annotations = [a for p in previous_ledgers for a in json.loads(p.read_text())["annotations"]]
    previous_by_claim = {a["claim_id"]: a for a in prior_annotations}
    annotations = []
    returned = [dict(row) for row in base]
    returned_by_id = {row["row_id"]: row for row in returned}
    for judgment in judgments:
        row = by_batch[judgment["batch_id"]]
        previous = previous_by_claim.get(row["candidate_id"])
        annotations.append(dict(schema_version="1.2.0", record_type="annotation",
                                id="annotation-" + digest(f"{annotator}:{review_id}:{row['candidate_id']}:{submission_sha}".encode()),
                                claim_id=row["candidate_id"], batch_id=row["row_id"], origin="ai_assisted_reviewed",
                                annotator_id=annotator, codebook_version=row["codebook_version"], label=judgment["label"],
                                review_status="reviewed_non_independent", created_at=timestamp,
                                rationale=judgment["review_notes"], review_notes=judgment["review_notes"],
                                supersedes=previous["id"] if previous else None,
                                review_provenance=submission["review_provenance"], ai_assisted=True, independent_human=False,
                                scoring_status=judgment["scoring_status"]))
        edited = returned_by_id[row["row_id"]]
        edited.update(label=judgment["label"], annotator_id=annotator,
                      review_status="needs_adjudication" if judgment["batch_id"] == "B05" else "annotated",
                      review_notes=(edited["review_notes"] + "\n\n" if edited["review_notes"] else "") + judgment["review_notes"])
    validate_rows(returned, base)
    index = {r["id"]: r for r in records}
    parent = index[by_batch["B05"]["candidate_id"]]
    doc = index[parent["document_id"]]
    text = (cache / doc["text_path"]).read_text(encoding="utf-8")
    revision = repair_b05(parent, text, timestamp, annotator)
    revision_task = task(doc, index[parent["event_id"]], revision, text, "B05-R1", [parent["id"]])
    revision_task.update(queue_version="annotation-queue-1.1.0", selection_kind="review_requested_span_revision",
                         revision_of_candidate_id=parent["id"], original_batch_id="B05")
    REVISION_TASK_VALIDATOR.validate(revision_task)
    if any(revision_task[key] for key in ("label", "annotator_id", "review_status", "review_notes")):
        raise ValueError("Repaired B05 must remain unannotated")
    validate_dataset(records + prior_annotations + [revision] + annotations, cache)
    audit = audit_speakers(records, cache, annotations)
    private.mkdir(parents=True, exist_ok=True)
    write_immutable(private / "B05-R1.claim.json", revision)
    write_immutable(private / "B05-R1.task.json", revision_task)
    write_immutable(private / "overlay_records.json", [revision] + annotations)
    write_rows(private / "reviewed_first_batch", returned)
    next_rows = [dict(by_batch[f"B{i:02}"]) for i in range(6, 11)]
    if any(row[k] for row in next_rows for k in ("label", "annotator_id", "review_status", "review_notes")):
        raise ValueError("Next review rows must remain blank")
    write_rows(private / "B06-B10", next_rows)
    write_immutable(ledger_dir / (review_id + ".attribution_audit.json"), audit)
    ledger = dict(review_id=review_id, annotator_id=annotator, recorded_at=timestamp,
                  submission_sha256=submission_sha, original_batch_sha256=digest((batch_directory / "first_batch.jsonl").read_bytes()),
                  previous_review_sha256=digest(previous_ledgers[-1].read_bytes()) if previous_ledgers else None,
                  annotations=annotations,
                  span_revision=dict(original_candidate_id=parent["id"], revised_candidate_id=revision["id"],
                                     document_id=revision["document_id"], event_id=revision["event_id"],
                                     text_sha256=revision["text_sha256"], start=revision["start"], end=revision["end"],
                                     file_sha256=digest((private / "B05-R1.claim.json").read_bytes()),
                                     final_stance="pending", private_path=str((private / "B05-R1.claim.json").relative_to(ROOT.parent))),
                  attribution_audit=review_id + ".attribution_audit.json",
                  independent_annotation_count=0,
                  history_policy="Append-only reviewed decisions; original candidate/batch/corpus and prior source audit remain unchanged. Corrections require a new review and supersedes link.")
    write_immutable(ledger_path, ledger)
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT.parent / ".local/pilot-v1")
    parser.add_argument("--batch-directory", type=Path, default=ROOT.parent / ".local/annotation-v1")
    parser.add_argument("--submission", type=Path, default=ROOT / "annotations/v1/reviews/Badr_A/submission-0001.json")
    args = parser.parse_args()
    ledger = record_review(args.cache, args.batch_directory, args.submission)
    print(f"Recorded/verified {len(ledger['annotations'])} reviewed assisted judgments; independent count 0. B05 revision {ledger['span_revision']['start']}:{ledger['span_revision']['end']} remains pending.")


if __name__ == "__main__":
    main()
