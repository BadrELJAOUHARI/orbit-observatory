"""Reproduce metadata/extraction checks; content screens are assistant review, not labels."""

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from .collect import utcnow, write_json
from .text import PageText, normalize
from .validation import ROOT, digest, load_config, validate_dataset

# Ordered as territorial recognition, withdrawal, military assistance, sanctions,
# responsibility. P means material to review, N means no explicit target found in
# this assistant screen, X means temporally inapplicable. None is a human label.
SCREENS = {
    "doc-us2014": ("PNNNX", "Joint press availability includes a Ukrainian prime minister and questions. Obama's Crimea/referendum remarks require exact legal/territorial scope review; Yatsenyuk's withdrawal demand is not a US claim."),
    "doc-us2022": ("PNPPP", "Prepared presidential remarks plus reporter questions and answers. Defensive aid must be separated from rejection of US combat deployment; NATO deployments are not Russian withdrawal; quoted Kremlin claims are explicitly rejected."),
    "doc-eu-unga77": ("PPNPP", "Illegal border change, withdrawal, sanctions and invasion attribution appear in context. Military/weapon keywords also describe Russian action, not EU assistance. Collective-EU passage mandate remains a release gate."),
    "doc-eu-unga78": ("NNPPP", "French source: general integrity principles, Russia's war of conquest, Ukraine's self-defence and Security Council sanctions/veto. Self-defence is not automatically an external weapons commitment. French and common-position review required."),
    "doc-tur-unga77": ("NNNNN", "Ukraine's integrity/independence and diplomacy are discussed without precise border/legal-recognition commitments. Other passages concern Syria, Libya, China and Palestine. English PDF explicitly says UNOFFICIAL TRANSLATION."),
    "doc-tur-unga78": ("NNNNN", "Ukraine diplomacy and independence/integrity are discussed without exact border/annexation scope. Other integrity passages concern Syria, Iraq, Yemen, Azerbaijan and China. PDF says Courtesy Translation and Check against delivery."),
    "doc-ind-unga77": ("NNNNN", "Ukraine, peace and general UN Charter principles do not by themselves settle the five exact targets. Sanctions passages concern UN counterterrorism; assistance includes disaster relief. PDF says CHECK AGAINST DELIVERY."),
    "doc-ind-unga78": ("NNNNN", "No explicit Ukraine mention in the extracted statement. Generic integrity/non-interference and Global South themes are not exact Ukraine stances. Retain the genuine document, including for no-stance and retrieval review."),
    "doc-zaf-unga77": ("NNNNN", "War in Eastern Europe and general dialogue appear, but no explicit Ukraine mention. Other conflicts, nuclear weapons, colonialism and Western Sahara create false keyword matches."),
    "doc-zaf-unga78": ("NNNNN", "African Peace Initiative and every country's integrity are discussed in Ukraine context, without precise Ukrainian border recognition. Annexation discussion concerns Israel/Palestine; sanctions concern Cuba/Zimbabwe."),
}


def review(output, destination):
    records = json.loads((output / "records.json").read_text())
    validate_dataset(records, output)
    actors, lenses = load_config()
    manifest = json.loads((ROOT / "source_manifest/v1/pilot.json").read_text())
    sources = {e["id"]: e for e in manifest["sources"]}
    results = []
    for doc in records:
        if doc["record_type"] != "document":
            continue
        entry = sources[doc["id"]]
        text = (output / doc["text_path"]).read_text(encoding="utf-8")
        cache_key = digest(entry["url"].encode())
        landing = json.loads((output / "cache" / (cache_key + ".json")).read_text())
        raw = (output / landing["raw_path"]).read_bytes()
        if digest(raw) != landing["raw_sha256"]:
            raise ValueError("Source verification page checksum mismatch")
        parser = PageText()
        parser.feed(raw.decode("utf-8"))
        page = normalize("".join(parser.parts))
        event_date = date.fromisoformat(entry["event_date"])
        if doc["actor_id"] == "USA":
            expected_speaker = "President Obama" if doc["id"] == "doc-us2014" else "President Biden"
            expected_date = event_date.strftime("%B %d, %Y")
            if expected_speaker not in raw.decode() or expected_date not in raw.decode():
                raise ValueError("US archive speaker/date verification failed")
            heading = expected_speaker + "; " + expected_date + "; White House archive"
            if doc["id"] == "doc-us2014" and "Office of the Press Secretary" not in page:
                raise ValueError("White House issuing-office verification failed")
        else:
            pos = page.index("Statement\n" + actors[doc["actor_id"]]["name"])
            heading = page[pos:page.index("\nKaltura", pos)]
            expected_date = f"{event_date.day} {event_date.strftime('%B %Y')}"
            if expected_date not in heading:
                raise ValueError("UN actor/date verification failed")
            expected_role = {"EU": "President of the European Council", "IND": "Minister for External Affairs", "TUR": "President", "ZAF": "Minister for International Relations and Cooperation" if "77" in doc["id"] else "President"}[doc["actor_id"]]
            if expected_role not in heading:
                raise ValueError("UN institution/role verification failed")

        screen, finding = SCREENS[doc["id"]]
        pdf = entry["extraction"]["kind"] == "un_statement_pdf"
        problems = ["PDF line wrapping fragments semantic claims; do not label without surrounding context.",
                    "Page numbers and running headers are retained in orbit-text-v1; offsets refer to that frozen text.",
                    "Published prepared statement is not independently checked against the delivered audio/video."] if pdf else ["Presidential transcript includes questions/other voices; document issuer is not per-passage attribution."]
        if doc["id"] == "doc-us2014":
            problems.append("Foreign-speaker block starts at PRIME MINISTER YATSENYUK and must not be attributed to USA.")
        if doc["id"] == "doc-eu-unga77":
            problems.append("Some sentence boundaries are glued by PDF layout, for example thing.In; do not silently repair this frozen text.")
        if doc["actor_id"] == "TUR":
            problems.append("English translation is source-provided but marked unofficial/courtesy; Turkish original and translator certification not obtained.")
        if doc["language"] == "fr":
            problems.append("Original French is the evidence; bilingual human review required. No machine translation supplied.")
        statuses = {"P": "potential_material_human_decision_required", "N": "no_explicit_target_found_in_assistant_screen", "X": "not_applicable"}
        result = dict(document_id=doc["id"], event_id=doc["event_id"], actor_id=doc["actor_id"],
                      issuer=doc["issuer"], delivery_date=doc["delivery_date"], publication_date=doc["publication_date"],
                      source_url=doc["canonical_url"], attachment_url=doc["resolved_url"], language=doc["language"],
                      raw_sha256=doc["raw_sha256"], text_sha256=doc["text_sha256"],
                      source_verification=dict(landing_url=entry["url"], landing_raw_sha256=landing["raw_sha256"],
                                               official_heading=heading, actor_institution_stated_date_verified=True,
                                               date_limit="Official stated event date, not an independent audiovisual delivery check."),
                      scope_status="representation_verified_common_position_gate_pending" if doc["actor_id"] == "EU" else "official_source_verified_passage_attribution_pending",
                      eu_representation=None, extraction_problems=problems,
                      translation_provenance=doc["translation_provenance"],
                      findings=finding,
                      lens_screen={lens_id: statuses[flag] for lens_id, flag in zip(lenses, screen)},
                      human_evidence_eligibility="not_adjudicated_for_any_lens",
                      release_eligible=False,
                      statistics=dict(characters=len(text), lines=len(text.splitlines()),
                                      numeric_only_lines=sum(bool(re.fullmatch(r"\d+", line)) for line in text.splitlines()),
                                      candidates=sum(r["record_type"] == "claim" and r["document_id"] == doc["id"] for r in records)))
        if doc["actor_id"] == "EU":
            result["eu_representation"] = dict(
                verified="Official UN docket identifies European Union, Charles Michel and President of the European Council, not a Belgian national delegation or a Commission-only speaker.",
                literal_on_behalf_formula_in_speech=bool(re.search(r"on behalf|au nom", text, re.I)),
                qualification="Delegation representation is corroborated explicitly by the UN actor heading and role. Neither normalized speech contains the literal on behalf/au nom formula. That is not proof each sentence is an adopted common position; obtain passage-specific common-position/mandate corroboration before release scoring.")
        results.append(result)
    audit = dict(audit_version="source-review-1.0.0", generated_at=utcnow(),
                 review_origin="assistant_source_quality_review_not_human_annotation",
                 records_sha256=digest((output / "records.json").read_bytes()),
                 documents=results,
                 limitations=["Lens screens are provisional assistant analysis, not human labels, model predictions or validated absences.",
                              "All human evidence eligibility remains unadjudicated; provenance verification does not create a stance.",
                              "EU common-position and translation qualifications remain gates, rather than assumed approvals."],
                 storage_check=dict(cached_documents_verified=len(results),
                                    verified_now=True,
                                    observation="Prior-milestone raw/text files exist in this attached workspace and pass saved hashes. Fresh-machine restoration has not been tested.",
                                    private_cache="../.local/pilot-v1", fresh_machine_restore_tested=False))
    if len(results) != 10 or Counter(r["actor_id"] for r in results) != Counter({a: 2 for a in actors}):
        raise ValueError("Expected ten pilot documents, two per actor")
    write_json(destination, audit)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT.parent / ".local/pilot-v1")
    parser.add_argument("--output", type=Path, default=ROOT / "data/pilot-v1/source_review.json")
    args = parser.parse_args()
    audit = review(args.cache, args.output)
    print(f"Verified source metadata and artifacts for {len(audit['documents'])} documents; human stance eligibility remains pending.")


if __name__ == "__main__":
    main()
