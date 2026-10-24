"""Boundary audit of frozen candidate spans; no source edits or stance labels."""

import re
from collections import Counter


def header_line(line):
    line = line.strip()
    return bool(re.fullmatch(r"\d+|V\d+|-?Courtesy Translation-?|UNOFFICIAL TRANSLATION|CHECK AGAINST DELIVERY", line, re.I)
                or re.match(r"(?i)^(?:as on september|\d+(?:TH|ST|ND|RD) UN GENERAL ASSEMBLY|UN GENERAL ASSEMBLY|NEW YORK, USA|\d{1,2} SEPTEMBER \d{4})", line))


def terminal(text):
    text = text.rstrip().rstrip('"\u201d\u2019\u00bb\')]}').rstrip()
    if re.search(r"(?:\bMr|\bMrs|\bMs|\bDr|\bProf|\bH\.E|\bU\.S)\.$", text, re.I):
        return False
    return bool(re.search(r"[.!?\u2026]$", text))


def boundary_flags(text, start, end):
    quote = text[start:end]
    previous = text[:start].rstrip()
    lines = previous.split("\n")
    skipped = 0
    while lines and header_line(lines[-1]):
        lines.pop()
        skipped += 1
    prefix = "\n".join(lines).rstrip()
    flags = []
    speaker = bool(re.match(r"(?:PRESIDENT [^:]+:|PRIME MINISTER [^:]+:|THE PRESIDENT:|Q\s)", quote))
    if prefix and not terminal(prefix) and not speaker:
        flags.append("possible_missing_sentence_start")
    if not terminal(quote):
        flags.append("possible_missing_sentence_end")
    if any(header_line(line) for line in quote.splitlines()):
        flags.append("retained_header_inside_span")
    return flags, skipped


def audit_boundaries(records, cache):
    docs = {r["id"]: r for r in records if r["record_type"] == "document"}
    texts = {identifier: (cache / doc["text_path"]).read_text(encoding="utf-8") for identifier, doc in docs.items()}
    findings = []
    for claim in records:
        if claim["record_type"] != "claim":
            continue
        doc = docs[claim["document_id"]]
        text = texts[doc["id"]]
        if text[claim["start"]:claim["end"]] != claim["quote"]:
            raise ValueError("Boundary audit found invalid source offsets")
        flags, skipped = boundary_flags(text, claim["start"], claim["end"])
        findings.append(dict(candidate_id=claim["id"], document_id=doc["id"], event_id=claim["event_id"],
                             text_sha256=claim["text_sha256"], start=claim["start"], end=claim["end"],
                             record_group="span_revision" if claim.get("revision_of") else "original_candidate",
                             language=doc["language"], source_format="html" if doc["actor_id"] == "USA" else "pdf",
                             flags=flags, status="boundary_review_required" if flags else "no_heuristic_boundary_problem_detected",
                             skipped_preceding_header_lines=skipped,
                             annotation_action="flag_only_preserve_existing_labels", stance_label_assigned=False))
    groups = {}
    for group in ("original_candidate", "span_revision"):
        subset = [f for f in findings if f["record_group"] == group]
        groups[group] = dict(total=len(subset), flagged=sum(bool(f["flags"]) for f in subset),
                             by_format={fmt: dict(total=sum(f["source_format"] == fmt for f in subset),
                                                  flagged=sum(f["source_format"] == fmt and bool(f["flags"]) for f in subset)) for fmt in ("html", "pdf")})
    return dict(audit_version="boundary-audit-1.0.0", review_origin="assistant_heuristic_screen_not_human_annotation",
                root_cause="orbit-text-v1 retains PDF physical line breaks; candidate_spans selects each newline-separated line, despite its legacy paragraph terminology. A PDF line is not a semantic sentence or atomic claim.",
                policy="No normalization, candidate, annotation, source hash or offset is overwritten. Audit flags are not stance labels or proof of grammatical completeness.",
                limitations=["Punctuation, abbreviations, headings and multilingual layout can cause false positives/negatives.",
                             "A complete sentence can still lack the actor, policy scope, antecedent or date needed for a complete claim.",
                             "Future sentence segmentation must be versioned and retain source-index mappings, speaker boundaries and human review."],
                counts=groups, flag_counts=dict(Counter(flag for f in findings for flag in f["flags"])), findings=findings)
