# Focal acquisition increment v2

Completed 25 October 2026; source-event cutoff 24 October. All counts are actual, post-admission counts. Existing strict definitions, W1, 113 completed reviews, training authorizations, reserved groups, approved website design and public scores are preserved.

## Results

- 245 recorded discovery queries and 923 distinct attempted document URLs across 64 saved batches. 579 dated original documents stored, including 77 reserved documents; downloads are not useful-stance counts. Stored actor counts: India 420, Türkiye 75, South Africa 46, EU 38. Bulk UK and USA responsibility acquisition stayed paused.
- **Strict supplement: 48 pairs / 46 passages / 25 events / 25 leakage groups.** Seven pairs are genuinely newly collected; 41 recover previously held evidence. Four genuinely new strict-target event families. All 48 are review candidates, not newly approved gold labels.
- **Component supplement: 171 pairs / 117 events / 114 groups.** 78 newly collected, 93 previously held evidence reclassified for component review. Their full-target scope holds remain. Territorial components 170; withdrawal component 1. All five lenses also have experimental component fields alongside eligible strict tasks. Component evidence is not technically defective merely because the strict compound target is incomplete.
- Combined supplement: **219 pairs / 210 distinct spans / 124 event records / 121 conservative event/copy groups**. This includes 85 genuinely new pairs across 63 event records, 61 groups; 59 event families / 57 groups are entirely new to earlier source inventory. Shared statements are one event, with named co-signatories retained.
- The **200 new-pair / 60 new-event goal was not met**: 85 new useful pairs, 59 entirely new event families but 57 conservative new groups. Recovered evidence is separate; no scope relaxation or duplicate claims met a quota. The old 561 packet is unchanged; combined strict corpus is 609 pairs.

## Actor coverage

Groups conservatively bind events/copies/translations/overlapping passages; group counts are not independent annotators. Full 25-cell actor × lens before/after table and actor × lens × year table are in the packet.

| Actor | Strict pairs before → after | Strict groups before → after | Additional component pairs / groups |
|---|---:|---:|---:|
| USA | 141 → 155 | 47 → 51 | 53 / 27 |
| EU | 47 → 79 | 14 → 23 | 43 / 27 |
| TUR | 0 → 2 | 0 → 2 | 37 / 27 |
| IND | 0 → 0 | 0 → 0 | 31 / 26 |
| ZAF | 1 → 1 | 1 → 1 | 7 / 7 |

Auxiliary UK remains 372 strict pairs and is not a displayed actor. No new UK labeling workload was created. India/Türkiye/South Africa now have substantive component evidence; zero new India/South Africa **full-target** cases does not mean political neutrality or absence of policy. New strict lens counts: responsibility 25, sanctions 17, withdrawal 4, military assistance 1, territorial recognition 1. This selected training-acquisition corpus is not an annual-position sample.

## Recovery and source audit

All **691** old held development pairs were audited with overlapping A technical/source, B target/component insufficiency, C endorsement/stance ambiguity and D irrelevant/duplicate categories. The original file and flags remain intact. There are 134 case-ledger records and 131 documented hold-clearance actions; 41 strict recovered tasks and 93 previously held component tasks enter this supplement. A ledger action does not imply that every hold on its record is cleared.

Each clearance records the original/replacement IDs, previous hold, exact proof offsets/text/hash, source URL, criterion, method and remaining holds. Sentence/paragraph repairs create new span IDs linked to originals; no old annotation is automatically transferred. Named joint-party formulae permit focal attribution of eight previously auxiliary-published events, preserving one shared event and other actual issuing parties. The dated MEA briefing's delivery date (24 February 2022) is distinguished from publication (25 February), with versioned date metadata.

Recovered sources include adopted Council texts, explicit Treasury issuer quotations and actually named joint parties. Reporter questions, foreign-only clauses, reported expert findings, unmandated Commission comments, provincial SA positions and translation qualifications remain separate. The same actor's name in a document title is insufficient. The admission audit caught foreign-speaker turns in India-hosted transcripts, Nordic/French-only clauses, western-Ukraine exodus language falsely matching “the West”, “Annexure I”, nonterritorial recognition, and unrelated Indo-Pacific/own-border language. These corrections are covered by focused checks.

Eighteen Türkiye URL failures were local Unicode encoding defects; a standard percent-encoding fix recovered ten additional original documents, without an alternate proxy or a permission bypass. Old failed receipts remain in attempt history. Other recorded outcomes include 185 × No Russia-Ukraine policy/conflict anchor, 53 × <urlopen error Tunnel connection failed: 403 Forbidden>, 49 × HTTP Error 403: Forbidden, 28 × Missing/out-of-period documentary event date, 13 × Not adopted Council common position, 10 × HTTP Error 404: Not Found, 4 × HTTP Error 503: Service Unavailable. Reasons remain per URL; these are not all network failures.

Current strict-held disposition: **126** records with remaining source/attribution/technical issues (often overlapping scope), **171** source-cleared component tasks retaining full-target scope holds, and **4** policy/own-direction insufficiencies. Overlapping remaining flags are in `acquisition_report.json`; source holds are never cleared by an AI suggestion or training approval. Twelve separately sampled, unlabeled development retrieval controls stay outside the main review count.

## Review and provenance

Download the supplemental ZIP and extract it. Open **strict/HTML** for full-target judgments and **components/HTML** for experimental component directions. Each file contains its scripts/data locally, with unreviewed/clean/quarantine, actor/lens/year/proposed-label filters, exact evidence/context/source links, autosave/status and portable CSV/JSON backups. The component banner and CSV `review_target` explicitly distinguish the task; the original strict proposition and scope hold remain visible. Review notes can correct proposed expression, scope, annexation or conditions without silently changing strict labels.

Browser checks passed on loopback HTTP. This managed Chromium blocks `file://` navigation by administrator policy; direct-file reopening could not be checked here and the policy was not bypassed. If local opening is restricted, run `python -m http.server 8765 --bind 127.0.0.1` inside the extracted packet and open its local index. CSV/JSON backups remain portable.

The strict CSV and component CSV have distinct candidate/packet IDs. Return their **complete exported CSVs**; filters do not omit rows. Enter Badr_A if that is your chosen annotator ID. Do not mark assisted review as blind independent. Current suggestions are **assistant-authored deterministic source/proposition/context rules**, not a new trained model or 222 independent LLM judgments. Strict suggestions: {'unresolved': 11, 'support': 37}; component suggestions: {'support': 135, 'unresolved': 36}. No new opposition/mixed coverage is fabricated, no Badr_A checks asserted, and no new training permission granted.

The existing return validator recognizes both packet versions, verifies immutable evidence/context/IDs and append-only provenance. Component returns write separate experimental-component records, never ordinary strict-target annotations or automatic training approvals. Existing 561/113 reviews remain frozen.

```bash
PYTHONPATH=python python -m orbit_data.review_import --help
```

## Protocol decision and training

See `COMPONENT_PROTOCOL_PROPOSAL_V1.md`: proposed direction, expression, scope, qualifications and independent quality dimensions; separate integrity direction/extent/annexation, withdrawal direction/extent/timing, and overall versus measure-specific aid/sanctions positions. `territorial_affected_records.csv` lists all 376 earlier partial-scope development IDs, including overlaps. Experimental new components are authorized; adopting them as production protocol still needs an explicit decision. No strict-label migration, W1 change, specificity-as-strength, arbitrary stance weights or neutral coding of no_stance/missing/unresolved occurs.

Aggregation is a proposal only: reviewed component distributions through the existing claim → event → quarter hierarchy, coverage/missingness, event-group uncertainty, and explicit-only versus implied-inclusive sensitivity. Representative actor-period scoring needs a separate sampling design and validation.

The approved freeze was **rechecked at 38 examples / eight events**, support 8 / no_stance 30. None of this increment's suggestions is approved for fitting. The existing two real baseline experiments and their negative/tiny-sample results were not rerun; no transformer, calibrated prediction or public score was produced. No approved-data eligibility changed materially.

## Reproduce, resume and storage

From the application directory `orbit-observatory/`:

```bash
PYTHONPATH=python python -m orbit_data.focal_collection --batches 50 --batch-size 20 --queries-per-batch 8 --finalize
PYTHONPATH=python python -m orbit_data.verify_focal
PYTHONPATH=python python -m unittest discover -s tests -p 'test_*.py'
```

The resume command reuses old/new successful and failed caches, request receipts, stable document/event IDs, source/query state and split assignments. It never re-downloads completed URLs merely to increase counts. Current pending productive URLs/queries: zero; two exhausted archive-form requests are deliberately deferred. New discovery leads must be explicitly queued; the checkpoint does not invent new work on every rerun. Queues and counters are saved after each batch. The main residual bottleneck is meaningful policy/component relevance and source/attribution clearance; direct discovery improved substantially through the MEA full-text route.

Original HTTP/PDF/JSON bytes and normalized text are separate. Extraction uses Unicode NFC, LF, collapsed within-line whitespace and unchanged stored physical lines; offsets are half-open Unicode code-point positions in that exact text. Reading aids carry source-character maps; raw content is never overwritten to reflow PDF text. Verifier reconstructs every development document from its cached original and checks protected prior artifacts and clearance proofs. Reserved bodies are not interpreted during verification/reporting.

Private technical checkpoint is incremental: restore the previous `orbit-acquisition-source-checkpoint-2026-10-24.zip`, then the new focal source delta into the repository root, preserving `.local/` and original paths. The new delta contains original new downloads/text, state, receipts, manifests, ledgers and supplemental packets. Technical reserved caches remain private and excluded from review exports. This workspace currently retains them; fresh-session persistence is not guaranteed. The private GitHub download branch supplies a retrievable backup. Public redistribution rights remain unresolved; keep original caches private and use receipt-based official retrieval where access permits.

See `RETRIEVAL_BENCHMARK_V2.md` for the 13-URL comparison, permitted methods, remaining failed URLs and optional existing-account Firecrawl adapter. Firecrawl is not connected here; no paid service or subscription was used. It cannot clear a scope/attribution defect.

**Next single milestone:** one consolidated return/adjudication of the supplemental strict and experimental component evidence, with a production-component protocol decision. That permits a new provenance-preserving readiness assessment; no further small batches or automatic public-score replacement.

## Final checks

129 Python checks pass. Both packet modes passed browser filtering, autosave/reload/full-profile restart, actual CSV download, CSV/JSON round trips, conflict/tampering rejection and storage-denial export fallback. Synthetic responses remained in /tmp. Thirteen packet/source/state artifacts are byte-identical on the idempotent rerun. All 94 protected prior artifacts remain unchanged; all 502 development documents reproduce from original cached responses, while 77 reserved receipts receive hash-only verification. No reserved-body interpretation occurs in reporting/verification.
