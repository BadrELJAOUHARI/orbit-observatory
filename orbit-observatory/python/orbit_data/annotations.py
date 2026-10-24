"""Prepare and validate private, unlabeled annotation files. No model calls."""

import argparse
import csv
import io
import json
import random
import re
import tarfile
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .collect import write_json
from .validation import ROOT, digest, load_config, validate_dataset

TASK_SCHEMA = json.loads((ROOT / "schemas/annotation-v1/task.schema.json").read_text())
TASK_VALIDATOR = Draft202012Validator(TASK_SCHEMA, format_checker=FormatChecker())
FIELDS = list(TASK_SCHEMA["properties"])
HUMAN_FIELDS = {"label", "annotator_id", "review_status", "review_notes"}
INTEGER_FIELDS = {"start", "end", "context_start", "context_end"}


def read_rows(path):
    if path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])) or set(reader.fieldnames or []) != set(FIELDS):
                raise ValueError("CSV must retain exactly the original, unique columns")
            rows = list(reader)
        for row in rows:
            for key in INTEGER_FIELDS:
                row[key] = int(row[key])
            if row["language_review_required"] not in {"true", "false"}:
                raise ValueError("Boolean CSV fields must be true or false")
            row["language_review_required"] = row["language_review_required"] == "true"
    else:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return rows


def write_rows(stem, rows):
    for suffix in (".csv", ".jsonl"):
        path = stem.with_suffix(suffix)
        if path.exists() and any(any(row.get(key) for key in HUMAN_FIELDS) for row in read_rows(path)):
            raise ValueError(f"Refusing to overwrite human work in {path}; use a new output directory")
    stem.parent.mkdir(parents=True, exist_ok=True)
    with stem.with_suffix(".csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (str(value).lower() if isinstance(value, bool) else value) for key, value in row.items()})
    stem.with_suffix(".jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def passage_id(doc, start, end):
    return "passage-" + digest(f"{doc['id']}:{doc['text_sha256']}:{start}:{end}".encode())


def task(doc, event, claim, text, row_id, related):
    start, end = claim["start"], claim["end"]
    context_start = max(0, start - 400)
    context_start = text.rfind("\n", 0, context_start) + 1
    context_end = text.find("\n", min(len(text), end + 400))
    if context_end < 0:
        context_end = len(text)
    _, lenses = load_config()
    return dict(queue_version="annotation-queue-1.0.0", record_type="annotation_task", row_id=row_id,
                candidate_id=claim["id"], selection_kind=claim.get("selection_kind", "retrieved_candidate"),
                passage_id=passage_id(doc, start, end), related_candidate_ids=";".join(sorted(related)),
                event_id=event["id"], document_id=doc["id"], actor_id=doc["actor_id"], event_date=event["event_date"],
                lens_id=claim["lens_id"], lens_proposition=lenses[claim["lens_id"]]["definition"],
                source_url=doc["canonical_url"], attachment_url=doc["resolved_url"], document_issuer=doc["issuer"],
                language=doc["language"], language_review_required=doc["language"] == "fr", text_sha256=doc["text_sha256"],
                start=start, end=end, exact_passage=text[start:end], context_start=context_start, context_end=context_end,
                context_before=text[context_start:start], context_after=text[end:context_end],
                offset_unit="unicode_code_point_half_open", codebook_version="1.0.0", translation_aid_id="",
                label="", annotator_id="", review_status="", review_notes="")


def build(cache):
    records = json.loads((cache / "records.json").read_text())
    validate_dataset(records, cache)
    indexed = {r["id"]: r for r in records}
    docs = {r["id"]: r for r in records if r["record_type"] == "document"}
    texts = {identifier: (cache / doc["text_path"]).read_text(encoding="utf-8") for identifier, doc in docs.items()}
    claims = sorted((r for r in records if r["record_type"] == "claim"), key=lambda r: (docs[r["document_id"]]["actor_id"], r["document_id"], r["start"], r["lens_id"]))
    groups = {}
    for c in claims:
        key = passage_id(docs[c["document_id"]], c["start"], c["end"])
        groups.setdefault(key, []).append(c["id"])
    queue = []
    for number, claim in enumerate(claims, 1):
        doc = docs[claim["document_id"]]
        related = [identifier for identifier in groups[passage_id(doc, claim["start"], claim["end"])] if identifier != claim["id"]]
        queue.append(task(doc, indexed[claim["event_id"]], claim, texts[doc["id"]], f"Q{number:04}", related))
    if len(queue) != 184:
        raise ValueError("This frozen preparation expects the original 184 candidates; create a new batch version for another corpus")
    spec = json.loads((ROOT / "annotations/v1/selection.json").read_text())
    if {identifier: d["text_sha256"] for identifier, d in docs.items()} != spec["corpus_text_hashes"]:
        raise ValueError("Frozen annotation corpus changed; preserve old text and create a new batch version")
    first = []
    for item in spec["retrieved"]:
        matches = [r for r in queue if all(r[key] == value for key, value in item.items())]
        if len(matches) != 1:
            raise ValueError(f"Frozen batch reference is missing or ambiguous: {item}")
        first.append(dict(matches[0]))

    # Stratified random controls from non-retrieved line units, not hand-selected misses.
    actors, lenses = load_config()
    rng = random.Random(spec["controls"]["seed"])
    populations = {}
    for actor in actors:
        population = []
        for identifier in sorted(docs):
            doc = docs[identifier]
            if doc["actor_id"] != actor:
                continue
            text = texts[identifier]
            pos = 0
            retrieved = [(c["start"], c["end"]) for c in claims if c["document_id"] == identifier]
            for line in text.split("\n"):
                end = pos + len(line)
                header = bool(re.match(r"(?i)^(?:as on september|check against delivery|address (?:by|to)|statement by|\d*th (?:un |session)|un general assembly)", line))
                if not header and len(line) >= 60 and sum(ch.isalpha() for ch in line) >= 40 and not any(pos < b and end > a for a, b in retrieved):
                    population.append((identifier, pos, end))
                pos = end + 1
        populations[actor] = len(population)
        identifier, start, end = rng.choice(population)
        doc = docs[identifier]
        event = indexed[doc["event_id"]]
        applicable = sorted(l["id"] for l in lenses.values() if l["applicable_from"] <= event["event_date"] and (not l["applicable_until"] or event["event_date"] <= l["applicable_until"]))
        lens = rng.choice(applicable)
        claim = dict(id="retrieval-control-" + digest(f"{identifier}:{doc['text_sha256']}:{start}:{end}:{lens}".encode()),
                     start=start, end=end, lens_id=lens, selection_kind="nonretrieved_random_control")
        first.append(task(doc, event, claim, texts[identifier], "pending", []))
    for number, row in enumerate(first, 1):
        row["row_id"] = f"B{number:02}"
    return queue, first, populations


def validate_rows(rows, expected, completed=False):
    expected = {r["candidate_id"]: r for r in expected}
    actual = {}
    for row in rows:
        TASK_VALIDATOR.validate(row)
        identifier = row["candidate_id"]
        if identifier in actual:
            raise ValueError("Duplicate candidate in annotation export")
        if identifier not in expected:
            raise ValueError("Unknown candidate or invented control")
        baseline = expected[identifier]
        for key in set(FIELDS) - HUMAN_FIELDS:
            if row[key] != baseline[key]:
                raise ValueError(f"Immutable field {key} changed for {row['row_id']}")
        if row["label"]:
            if not row["annotator_id"].strip() or row["review_status"] not in {"annotated", "needs_adjudication"}:
                raise ValueError("A human label requires an annotator ID and review status")
            if row["label"] in {"mixed", "unresolved"} and not row["review_notes"].strip():
                raise ValueError("Mixed/unresolved labels need explanatory notes")
        elif row["review_status"] == "annotated":
            raise ValueError("An annotated row cannot have an empty label")
        if row["review_status"] == "needs_language_review" and (row["label"] or not row["review_notes"].strip()):
            raise ValueError("Language deferral requires an empty label and explanatory notes")
        if completed and (not row["label"] or row["review_status"] != "annotated"):
            raise ValueError("Completed export still contains undecided/deferred rows")
        actual[identifier] = row
    if set(actual) != set(expected):
        raise ValueError("Annotation export dropped rows")
    return Counter(r["label"] or "pending" for r in rows)


def render_batch(rows, output):
    parts = ["# First annotation batch: 20 retrieved candidates + 5 random controls\n\n",
             "Use codebooks/v1.0.0/README.md and the five lens sheets. Labels and annotator IDs are intentionally empty. No machine labels or translations are supplied.\n\n",
             "Read here; enter decisions in a copy of first_batch.csv or first_batch.jsonl. Edit only label, annotator_id, review_status and review_notes. Keep source text and offsets unchanged. Review the exact central passage with context; request expansion/splitting when needed. A source issuer is not proof of the speaker of each line.\n\n",
             "B01–B20 are a diagnostic selection, not an unbiased test set. B21–B25 are seeded non-retrieved controls, one per actor. Matching passage_id values refer to the same passage, not new events. French can be deferred with an empty label and needs_language_review status.\n\n"]
    for row in rows:
        parts.extend([f"## {row['row_id']} · {row['actor_id']} · {row['event_date']} · {row['lens_id']}\n\n",
                      f"Proposition: {row['lens_proposition']}\n\n",
                      f"Source: {row['source_url']}\n\nLanguage: {row['language']}; document: {row['document_id']}; event: {row['event_id']}.\n\n",
                      f"Candidate: {row['candidate_id']}\n\nPassage group: {row['passage_id']}; offsets [{row['start']}, {row['end']}).\n\n",
                      "Context before:\n\n```text\n" + row["context_before"] + "\n```\n\n",
                      "**Exact passage to label:**\n\n```text\n" + row["exact_passage"] + "\n```\n\n",
                      "Context after:\n\n```text\n" + row["context_after"] + "\n```\n\n",
                      "Response fields in CSV/JSONL: label, annotator_id, review_status, review_notes.\n\n"])
    (output / "first_batch.md").write_text("".join(parts), encoding="utf-8")


def prepare(cache, output):
    audit = json.loads((ROOT / "data/pilot-v1/source_review.json").read_text())
    if audit["records_sha256"] != digest((cache / "records.json").read_bytes()):
        raise ValueError("Source review is stale for this record snapshot; review the changed provenance first")
    queue, first, populations = build(cache)
    validate_rows(queue, queue)
    validate_rows(first, first)
    # Check all existing exports before any overwrite, preserving partial human work.
    for stem in ("queue", "first_batch"):
        for suffix in (".csv", ".jsonl"):
            path = output / (stem + suffix)
            if path.exists() and any(any(row.get(k) for k in HUMAN_FIELDS) for row in read_rows(path)):
                raise ValueError(f"Refusing to overwrite human work: {path}")
    write_rows(output / "queue", queue)
    write_rows(output / "first_batch", first)
    render_batch(first, output)
    for name, expected in (("queue", queue), ("first_batch", first)):
        for suffix in (".csv", ".jsonl"):
            validate_rows(read_rows(output / (name + suffix)), expected)
    meta = dict(preparation_version="annotation-prep-1.0.0", codebook_version="1.0.0",
                records_sha256=digest((cache / "records.json").read_bytes()),
                selection_sha256=digest((ROOT / "annotations/v1/selection.json").read_bytes()),
                codebooks_sha256=digest((ROOT / "codebooks/v1.0.0/codebooks.json").read_bytes()),
                source_review_sha256=digest((ROOT / "data/pilot-v1/source_review.json").read_bytes()),
                queue_count=len(queue), first_batch_count=len(first),
                unique_retrieved_passages=len({r["passage_id"] for r in queue}),
                first_batch_ids=[r["candidate_id"] for r in first],
                control_population_by_actor=populations,
                random_seed=20261023, human_labels=0, machine_labels=0, translation_aids=0,
                artifacts={p.name: digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file() and p.suffix in {".csv", ".jsonl", ".md"}})
    write_json(output / "manifest.json", meta)
    return meta


def bundle(cache, output, destination):
    files = {}
    for base, prefix in ((cache, "pilot-v1"), (output, "annotation-v1")):
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                raise ValueError("Refusing symlink in private bundle")
            if path.is_file():
                files[prefix + "/" + str(path.relative_to(base))] = path
    for relative in ("codebooks/v1.0.0", "schemas", "configs/v1", "source_manifest/v1", "annotations/v1", "python/orbit_data"):
        for path in sorted((ROOT / relative).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                files["application/" + str(path.relative_to(ROOT))] = path
    for relative in ("requirements-data.txt", "data/pilot-v1/source_review.json", "docs/ANNOTATION_REVIEW.md", "docs/SOURCE_QUALITY_REVIEW.md", "docs/DATA_PILOT.md"):
        files["application/" + relative] = ROOT / relative
    checksums = {name: digest(path.read_bytes()) for name, path in files.items()}
    manifest = json.dumps(dict(private_research_bundle=True, redistribution_clearance=False, sha256=checksums), indent=2).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as tar:
        for name, path in files.items():
            tar.add(path, arcname="orbit-review-v1/" + name, recursive=False)
        info = tarfile.TarInfo("orbit-review-v1/BUNDLE_MANIFEST.json")
        info.size = len(manifest)
        tar.addfile(info, io.BytesIO(manifest))
    # Verify the actual archive rather than trusting its existence.
    with tarfile.open(destination) as tar:
        for name, sha in checksums.items():
            if digest(tar.extractfile("orbit-review-v1/" + name).read()) != sha:
                raise ValueError("Private archive verification failed")
    destination.with_suffix(destination.suffix + ".sha256").write_text(digest(destination.read_bytes()) + "  " + destination.name + "\n")
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "validate", "bundle"])
    parser.add_argument("--cache", type=Path, default=ROOT.parent / ".local/pilot-v1")
    parser.add_argument("--output", type=Path, default=ROOT.parent / ".local/annotation-v1")
    parser.add_argument("--file", type=Path, help="Returned CSV/JSONL for validation")
    parser.add_argument("--kind", choices=["queue", "first_batch"], default="first_batch")
    parser.add_argument("--completed", action="store_true")
    parser.add_argument("--archive", type=Path, default=ROOT.parent / ".local/orbit-review-v1.tar.gz")
    args = parser.parse_args()
    if args.command == "prepare":
        meta = prepare(args.cache, args.output)
        print(f"Prepared {meta['queue_count']} unlabeled tasks and {meta['first_batch_count']} first-batch rows at {args.output}")
    elif args.command == "validate":
        queue, first, _ = build(args.cache)
        rows = read_rows(args.file or args.output / (args.kind + ".csv"))
        counts = validate_rows(rows, queue if args.kind == "queue" else first, args.completed)
        print(f"Validated {len(rows)} rows: {dict(counts)}. Human judgments are not model predictions.")
    else:
        print(f"Verified private bundle with {bundle(args.cache, args.output, args.archive)} files: {args.archive}")


if __name__ == "__main__":
    main()
