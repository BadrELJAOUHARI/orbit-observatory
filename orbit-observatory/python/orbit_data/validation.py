"""JSON Schema shape checks plus cross-record provenance/offset checks."""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas/v1/records.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
ANNOTATION_1_1 = Draft202012Validator(
    json.loads((ROOT / "schemas/v1.1/annotation.schema.json").read_text()),
    format_checker=FormatChecker(),
)
ANNOTATION_1_2 = Draft202012Validator(
    json.loads((ROOT / "schemas/v1.2/annotation.schema.json").read_text()),
    format_checker=FormatChecker(),
)
ANNOTATION_1_3 = Draft202012Validator(
    json.loads((ROOT / 'schemas/v1.3/annotation.schema.json').read_text()), format_checker=FormatChecker())
CLAIM_1_1 = Draft202012Validator(
    json.loads((ROOT / "schemas/v1.1/claim.schema.json").read_text()),
    format_checker=FormatChecker(),
)
CLAIM_2_0 = Draft202012Validator(
    json.loads((ROOT / "schemas/v2/claim.schema.json").read_text()),
    format_checker=FormatChecker(),
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_config():
    actors = json.loads((ROOT / "configs/v1/actors.json").read_text())
    lenses = json.loads((ROOT / "configs/v1/lenses.json").read_text())
    return {a["id"]: a for a in actors["actors"]}, {l["id"]: l for l in lenses["lenses"]}


def validate_record(record):
    if record.get("record_type") == "claim" and record.get("schema_version") == "2.0.0":
        CLAIM_2_0.validate(record)
    elif record.get("record_type") == "annotation" and record.get("schema_version") == "1.3.0":
        ANNOTATION_1_3.validate(record)
    elif record.get("record_type") == "annotation" and record.get("schema_version") == "1.2.0":
        ANNOTATION_1_2.validate(record)
        if record["review_notes"] != record["rationale"]:
            raise ValueError("Reviewed reasoning must agree with the legacy rationale field")
    elif record.get("record_type") == "claim" and record.get("schema_version") == "1.1.0":
        CLAIM_1_1.validate(record)
    elif record.get("record_type") == "annotation" and record.get("schema_version") == "1.1.0":
        ANNOTATION_1_1.validate(record)
    else:
        VALIDATOR.validate(record)
    if record["record_type"] == "prediction" and record["eligibility"] == "stance_bearing":
        if abs(record["stance_score"] - (2 * record["support_probability"] - 1)) > 1e-12:
            raise ValueError("Prediction stance must equal 2*p-1")


def validate_manifest(manifest):
    actors, _ = load_config()
    if manifest["schema_version"] != "1.0.0":
        raise ValueError("Unsupported manifest version")
    entries = {e["id"]: e for e in manifest["sources"]}
    if len(entries) != len(manifest["sources"]):
        raise ValueError("Duplicate manifest IDs")
    required = {"id", "actor_id", "event_id", "event_date", "delivery_date", "publication_date",
                "date_basis", "title", "issuer", "publisher", "url", "language", "stream",
                "extraction", "identity_markers", "duplicate_of", "translation_of", "translation_provenance"}
    for e in entries.values():
        if set(e) != required:
            raise ValueError(f"Manifest fields differ for {e.get('id')}")
        a = actors[e["actor_id"]]
        if urlsplit(e["url"]).scheme != "https" or urlsplit(e["url"]).hostname not in a["official_hosts"]:
            raise ValueError("Manifest source is not an approved official HTTPS host")
        for key in ("event_date", "delivery_date", "publication_date"):
            if e[key] is not None:
                FormatChecker().check(e[key], "date")
        if e["event_date"] is None or not e["identity_markers"]:
            raise ValueError("Manifest needs event date and source identity markers")
        for key in ("duplicate_of", "translation_of"):
            if e[key] is not None:
                other = entries[e[key]]
                if other["id"] == e["id"] or other["event_id"] != e["event_id"]:
                    raise ValueError("Copies/translations must share an event")
        if e["translation_of"] and not e["translation_provenance"]:
            raise ValueError("Translation provenance required")
        for other in entries.values():
            if other["event_id"] == e["event_id"] and (other["event_date"] != e["event_date"] or other["stream"] != e["stream"]):
                raise ValueError("One event cannot have conflicting dates/streams")
        for relation in ("duplicate_of", "translation_of"):
            visited = {e["id"]}
            target = e[relation]
            while target:
                if target in visited:
                    raise ValueError("Cyclic copy/translation relation")
                visited.add(target)
                target = entries[target][relation]
    return entries


def safe_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes output directory")
    return path


def validate_dataset(records, output):
    actors, lenses = load_config()
    indexed = {}
    candidate_v2_keys = set()
    for record in records:
        validate_record(record)
        if record["id"] in indexed:
            raise ValueError("Duplicate record ID")
        if record["record_type"] == "claim" and record["schema_version"] == "2.0.0":
            key = tuple(record[k] for k in ("document_id", "text_sha256", "event_id", "lens_id", "start", "end"))
            if key in candidate_v2_keys:
                raise ValueError("Duplicate v2 candidate evidence for the same event/lens")
            candidate_v2_keys.add(key)
        indexed[record["id"]] = record

    def ref(identifier, kind):
        r = indexed[identifier]
        if r["record_type"] != kind:
            raise ValueError(f"Expected {kind}: {identifier}")
        return r

    texts = {}
    for r in records:
        kind = r["record_type"]
        if kind == "document":
            actor = actors[r["actor_id"]]
            if urlsplit(r["canonical_url"]).hostname not in actor["official_hosts"]:
                raise ValueError("Document canonical host outside actor source scope")
            raw = safe_path(output, r["raw_path"]).read_bytes()
            text_raw = safe_path(output, r["text_path"]).read_bytes()
            if digest(raw) != r["raw_sha256"] or digest(text_raw) != r["text_sha256"]:
                raise ValueError("Artifact hash mismatch")
            texts[r["id"]] = text_raw.decode("utf-8")
            event = ref(r["event_id"], "event")
            if r["id"] not in event["document_ids"] or r["actor_id"] not in event["actor_ids"]:
                raise ValueError("Document/event membership mismatch")
            if r["delivery_date"] and r["delivery_date"] != event["event_date"]:
                raise ValueError("Delivery date does not match the communication event")
            for relation in ("duplicate_of", "translation_of"):
                if r[relation]:
                    other = ref(r[relation], "document")
                    if other["id"] == r["id"] or other["event_id"] != r["event_id"]:
                        raise ValueError("Copy/translation event mismatch")
                    if relation == "duplicate_of" and (other["text_sha256"] != r["text_sha256"] or other["language"] != r["language"]):
                        raise ValueError("Exact duplicate link must share text hash and language")
            if r["translation_of"] and not r["translation_provenance"]:
                raise ValueError("Translation provenance missing")
        elif kind == "event":
            if not r["document_ids"] or not r["actor_ids"]:
                raise ValueError("Empty communication event")
            for doc_id in r["document_ids"]:
                if ref(doc_id, "document")["event_id"] != r["id"]:
                    raise ValueError("Event/document membership mismatch")
        elif kind in ("annotation", "prediction"):
            ref(r["claim_id"], "claim")
            if kind == "annotation" and r["supersedes"]:
                previous = ref(r["supersedes"], "annotation")
                if previous["id"] == r["id"] or previous["claim_id"] != r["claim_id"]:
                    raise ValueError("Annotation correction must refer to an earlier annotation of the same claim")
    for r in records:
        if r["record_type"] != "claim":
            continue
        doc = ref(r["document_id"], "document")
        event = ref(r["event_id"], "event")
        lens = lenses[r["lens_id"]]
        if r.get("revision_of"):
            parent = ref(r["revision_of"], "claim")
            if parent["id"] == r["id"] or any(parent[key] != r[key] for key in ("document_id", "event_id", "lens_id", "text_sha256")):
                raise ValueError("Span revision must retain its original document/event/lens/text identity")
            if not r["start"] <= parent["start"] < parent["end"] <= r["end"]:
                raise ValueError("Expanded span must contain the original evidence")
            if (r["start"], r["end"]) == (parent["start"], parent["end"]):
                raise ValueError("An expansion revision must actually expand the evidence")
        if r["target_text"] != lens["definition"]:
            raise ValueError("Claim target does not match the versioned lens definition")
        if doc["event_id"] != event["id"] or doc["text_sha256"] != r["text_sha256"]:
            raise ValueError("Claim provenance mismatch")
        text = texts[doc["id"]]
        if not 0 <= r["start"] < r["end"] <= len(text) or text[r["start"]:r["end"]] != r["quote"]:
            raise ValueError("Evidence offsets do not reproduce stored text")
        if r.get("schema_version") == "2.0.0":
            indices = r["source_indices"]
            if (len(indices) != len(r["reading_text"]) or indices != sorted(set(indices))
                    or indices[0] != r["start"] or indices[-1] + 1 != r["end"]):
                raise ValueError("Invalid reading/source alignment")
            if "".join(" " if text[i] == "\n" else text[i] for i in indices) != r["reading_text"]:
                raise ValueError("Reading text does not map exactly to frozen source")
            for parent_id in r["derived_from"]:
                parent = ref(parent_id, "claim")
                if any(parent[k] != r[k] for k in ("document_id", "event_id", "lens_id", "text_sha256")):
                    raise ValueError("Candidate lineage crosses provenance")
                if parent["end"] <= r["start"] or parent["start"] >= r["end"]:
                    raise ValueError("Candidate lineage must overlap its evidence")
        if event["event_date"] < lens["applicable_from"] or (lens["applicable_until"] and event["event_date"] > lens["applicable_until"]):
            raise ValueError("Lens inapplicable at event date")
