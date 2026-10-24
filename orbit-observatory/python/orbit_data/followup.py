"""Record review-0002 and requested repairs without replacing frozen evidence."""

import json
from pathlib import Path

from .annotations import read_rows, task, validate_rows, write_rows
from .collect import utcnow
from .reviewed import REVISION_TASK_VALIDATOR, write_immutable
from .segmentation import audit_boundaries
from .validation import ROOT, digest, validate_dataset

WINDOWS = {
    "B06": ("And because we must stop the", "Kremlin’s war machine, massive economic sanctions were unavoidable."),
    "B07": ("The third lie is that the aggression against Ukraine", "Kremlin’s war machine, massive economic sanctions were unavoidable."),
    "B08": ("L’Union européenne soutiendra sans relâche l’Ukraine dans", "l’exercice de son droit à la légitime défense."),
    "B09": ("We will continue to increase our efforts to end the war, which has been", "independence of Ukraine."),
    "B10": ("We will continue to increase our efforts to end the war through diplomacy", "integrity."),
}


def expand(parent, text, row_id, timestamp, annotator):
    begin, ending = WINDOWS[row_id]
    start = text.rfind(begin, 0, parent["start"] + 1)
    final = text.find(ending, parent["start"])
    if start < 0 or final < 0:
        raise ValueError(f"Frozen repair anchors absent for {row_id}")
    end = final + len(ending)
    if not start <= parent["start"] < parent["end"] <= end or (start, end) == (parent["start"], parent["end"]):
        raise ValueError("Requested repair must expand and contain the original")
    revision = dict(parent)
    revision.update(schema_version="1.1.0", id="claim-revision-" + digest(
        f"{parent['id']}:{parent['text_sha256']}:{start}:{end}".encode()),
        start=start, end=end, quote=text[start:end], selection_method="review_requested_span_expansion_v1",
        revision_of=parent["id"], revision_reason=f"Badr_A requested {row_id} boundary repair; B07 includes multiple contiguous sentences to retain its parent and identify Ukraine/aggression and the Kremlin. No stance is inherited.",
        revision_requested_by=annotator, created_at=timestamp,
        unresolved_reason="Repaired candidate awaiting review of the expanded evidence, attribution, source qualifications and exact target scope.")
    return revision


def overlay_history(batch):
    indexed = {}
    for path in sorted((batch / "reviews").glob("*/*/overlay_records.json")):
        for record in json.loads(path.read_text()):
            if record["id"] in indexed and indexed[record["id"]] != record:
                raise ValueError("History contains conflicting versions under one record ID")
            indexed[record["id"]] = record
    return list(indexed.values())


def record_followup(cache, batch, submission_path):
    records = json.loads((cache / "records.json").read_text())
    history = overlay_history(batch)
    validate_dataset(records + history, cache)
    submission = json.loads(submission_path.read_text())
    if submission["annotator_id"] != "Badr_A" or not submission["ai_assisted"] or submission["independent_human"]:
        raise ValueError("Unexpected review provenance")
    ledger_dir = ROOT / "annotations/v1/reviews/Badr_A"
    ledger_path = ledger_dir / "review-0002.review.json"
    private = batch / "reviews/Badr_A/review-0002"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        if ledger["submission_sha256"] != digest(submission_path.read_bytes()):
            raise ValueError("Changed submission cannot overwrite review history")
        for name, sha in ledger["private_artifact_hashes"].items():
            if digest((private / name).read_bytes()) != sha:
                raise ValueError(f"Reviewed artifact changed: {name}")
        return ledger
    if submission["submission_id"] != "review-0002":
        raise ValueError("This command records the second pilot review only")
    original = read_rows(batch / "first_batch.jsonl")
    first_ledger = json.loads((ledger_dir / "review-0001.review.json").read_text())
    prepared = json.loads((batch / "manifest.json").read_text())
    if digest((batch / "first_batch.jsonl").read_bytes()) != prepared["artifacts"]["first_batch.jsonl"]:
        raise ValueError("Frozen batch checksum changed")
    mapping = {r["row_id"]: r for r in original}
    mapping["B05-R1"] = json.loads((batch / "reviews/Badr_A/review-0001/B05-R1.task.json").read_text())
    if {j["batch_id"] for j in submission["judgments"]} != {"B05-R1", *WINDOWS} or len(submission["judgments"]) != 6:
        raise ValueError("Expected exactly the six submitted second-round decisions")
    index = {r["id"]: r for r in records + history}
    timestamp = utcnow()
    annotations = []
    for judgment in submission["judgments"]:
        row = mapping[judgment["batch_id"]]
        previous = [a for a in history if a["record_type"] == "annotation" and a["claim_id"] == row["candidate_id"]]
        annotations.append(dict(schema_version="1.2.0", record_type="annotation", id="annotation-" + digest(
            f"Badr_A:review-0002:{row['candidate_id']}:{digest(submission_path.read_bytes())}".encode()),
            claim_id=row["candidate_id"], batch_id=row["row_id"], origin="ai_assisted_reviewed", annotator_id="Badr_A",
            codebook_version=row["codebook_version"], label=judgment["label"], review_status="reviewed_non_independent",
            created_at=timestamp, rationale=judgment["review_notes"], review_notes=judgment["review_notes"],
            supersedes=previous[-1]["id"] if previous else None, review_provenance=submission["review_provenance"],
            ai_assisted=True, independent_human=False, scoring_status=judgment["scoring_status"]))
    revisions, tasks, revision_metadata = [], [], []
    for row_id in WINDOWS:
        row = mapping[row_id]
        parent = index[row["candidate_id"]]
        doc = index[parent["document_id"]]
        text = (cache / doc["text_path"]).read_text(encoding="utf-8")
        revision = expand(parent, text, row_id, timestamp, "Badr_A")
        followup = task(doc, index[parent["event_id"]], revision, text, row_id + "-R1", [parent["id"]])
        followup.update(queue_version="annotation-queue-1.1.0", selection_kind="review_requested_span_revision",
                        revision_of_candidate_id=parent["id"], original_batch_id=row_id)
        REVISION_TASK_VALIDATOR.validate(followup)
        if any(followup[k] for k in ("label", "annotator_id", "review_status", "review_notes")):
            raise ValueError("Expanded candidates must remain pending")
        revisions.append(revision)
        tasks.append(followup)
        revision_metadata.append(dict(batch_id=followup["row_id"], original_candidate_id=parent["id"], revised_candidate_id=revision["id"],
                                      document_id=doc["id"], event_id=parent["event_id"], text_sha256=doc["text_sha256"],
                                      start=revision["start"], end=revision["end"], language=doc["language"],
                                      translation_provenance=doc["translation_provenance"], final_stance="pending"))
    validate_dataset(records + history + revisions + annotations, cache)
    audit = audit_boundaries(records + history + revisions, cache)
    by_id = {a["batch_id"]: a for a in annotations}
    conflict = dict(conflict_id="review-0002-B05-R1-scope", review_origin="assistant_codebook_consistency_check",
                    annotation_id=by_id["B05-R1"]["id"], candidate_id=mapping["B05-R1"]["candidate_id"], submitted_label="support",
                    target=mapping["B05-R1"]["lens_proposition"], status="requires_Badr_decision", effective_scoring_gate="blocked_scope_conflict",
                    codebook_version="1.0.0", explicit_all_territory=False, explicit_1991_borders=False,
                    issue="No stated territorial exception is not itself explicit comprehensive territorial scope under the frozen strict codebook. Preserve the submitted support label; do not infer recognized-border coverage or silently change the target.",
                    pending_protocol_proposal="codebooks/v1.0.1/SCOPE_CLARIFICATION.md", resolution=None)
    private.mkdir(parents=True, exist_ok=True)
    write_immutable(private / "overlay_records.json", revisions + annotations)
    write_immutable(private / "revisions.json", revisions)
    write_immutable(private / "repaired_tasks.json", tasks)
    write_immutable(private / "revision_metadata.json", revision_metadata)
    # Keep the first round's returned view and original B05 judgment intact.
    returned = read_rows(batch / "reviews/Badr_A/review-0001/reviewed_first_batch.jsonl")
    returned = [dict(r) for r in returned]
    for row in returned:
        if row["row_id"] not in WINDOWS:
            continue
        annotation = by_id[row["row_id"]]
        row.update(label=annotation["label"], annotator_id="Badr_A", review_status="needs_adjudication",
                   review_notes=(row["review_notes"] + "\n\n" if row["review_notes"] else "") + annotation["review_notes"])
    validate_rows(returned, original)
    write_rows(private / "reviewed_first_batch", returned)
    reviewed_b05 = dict(mapping["B05-R1"])
    reviewed_b05.update(label="support", annotator_id="Badr_A", review_status="needs_adjudication", review_notes=by_id["B05-R1"]["review_notes"])
    REVISION_TASK_VALIDATOR.validate(reviewed_b05)
    write_immutable(private / "reviewed_B05-R1.task.json", reviewed_b05)
    write_immutable(ledger_dir / "review-0002.scope_conflict.json", conflict)
    write_immutable(ledger_dir / "review-0002.boundary_audit.json", audit)
    ledger = dict(review_id="review-0002", recorded_at=timestamp, annotator_id="Badr_A",
                  submission_sha256=digest(submission_path.read_bytes()), previous_review_sha256=digest((ledger_dir / "review-0001.review.json").read_bytes()),
                  annotations=annotations, span_revisions=revision_metadata,
                  scope_conflict="review-0002.scope_conflict.json", boundary_audit="review-0002.boundary_audit.json",
                  independent_annotation_count=0, private_artifact_hashes={p.name: digest(p.read_bytes()) for p in private.iterdir() if p.is_file()},
                  history_policy="Append only. Submitted labels remain on their original candidate versions; expanded versions have no inherited label. No mass repair or rescore.")
    write_immutable(ledger_path, ledger)
    return ledger


def main():
    ledger = record_followup(ROOT.parent / ".local/pilot-v1", ROOT.parent / ".local/annotation-v1",
                             ROOT / "annotations/v1/reviews/Badr_A/submission-0002.json")
    print(f"Recorded/verified {len(ledger['annotations'])} assisted judgments and {len(ledger['span_revisions'])} pending repairs. B05-R1 scope conflict awaits Badr's decision.")


if __name__ == "__main__":
    main()
