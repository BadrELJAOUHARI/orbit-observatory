# Source-aligned segmentation v2

23 October 2026. Research preparation only; website, scores and source text unchanged.

Run from `/workspace/orbit-observatory/orbit-observatory`:

    PYTHONPATH=python python -m orbit_data.resegment
    PYTHONPATH=python python -m unittest discover -s tests -v

The command uses only `/workspace/orbit-observatory/.local/pilot-v1/` and existing review overlays. It makes no network requests, performs no collection and trains no model. It records/verifies review-0003 before generation. Do not rerun the legacy collector to obtain these candidates.

## Reading view and evidence

The root cause was v1's assumption that each LF represented a paragraph. PDF LF usually represents a physical layout line. V1 extraction and all normalized stored text are frozen; the new version reconstructs a separate reading view.

- Re-extract cached PDFs with pinned pypdf, requiring normalized content to match the stored source exactly. Recover physical-line offsets, page IDs and retained blank lines. Failure stops the command instead of silently creating new offsets.
- Recover likely paragraph gaps from uniquely matched PDF text chunks: vertical spacing greater than 1.6 times the page's median normal line gap. Ambiguous/unmatched geometry remains uncertain. Blank lines, measured gaps and addresses can separate paragraphs only after a completed sentence. A page change never forces a sentence or paragraph break. Paragraph recovery is a heuristic, not certification of original typography.
- Explicit, versioned body-start anchors separate titles/salutations from speech body. Running-header templates must match entire lines. A regression check ensures a body line beginning “UN General Assembly” survives. Omitted text, offsets, page and reason remain in the segmentation ledger; original document/translation qualifications are retained.
- Join physical lines with a reading space, mapping that space to the original LF. No spelling, hyphenation, translation or word-spacing correction occurs. Split English/French punctuation conservatively, retaining titles, initials, quotation marks and numeric artefacts for review. HTML paragraph and speaker-turn boundaries remain intact.
- Every reading character has a source index. `reading_text` is obtained from those indices with only LF-to-space substitution. `start`, `end` and `quote` always describe the exact contiguous source envelope. If a sentence crosses a removed page header, its raw envelope still contains that header, while its reading indices omit it. Two such candidate records remain explicitly flagged; do not present the cleaned view as an exact contiguous quotation.
- Neighboring complete units provide queue context. No context crosses an intervening speaker turn. Multi-sentence reviewed windows, particularly B07-R1's attribution chain, remain curated units alongside sentence candidates.

`schemas/v2/claim.schema.json` adds source alignment, segmentation version, paragraph ID, quality flags and many-to-many `derived_from` links. Claim schema 1.1.0's strict containment rule remains unchanged for the earlier manual expansions. V2 regeneration can split or merge overlapping evidence and therefore uses a separate contract. Dataset validation checks all references, exact raw offsets, reading alignment, lens/date applicability and duplicate event/document/lens spans.

## Preserved judgments and transfers

Review-0003 records B06-R1 support, B07-R1 support, B08-R1 no_stance, B09-R1 unresolved and B10-R1 unresolved. The full supplied reasoning is in `review_notes`, with Badr_A review, AI assistance and `independent_human=false`. There are 16 reviewed assisted decisions, zero independent judgments. Original annotations are retained on their original versions; five reviewed repairs do not overwrite their fragment parents.

W1 was explicitly selected. `codebooks/v1.0.2/decision.json` resolves the pending protocol choice, preserves B05-R1 support and its original hold reason, and excludes it from scoring. The comprehensive withdrawal target is unchanged. W2 is not applied. B09/B10's partial territorial-integrity evidence is retained with a scope-insufficiency reason and unofficial/courtesy translation qualifications.

Ten exact-evidence annotation transfers point to existing annotations under `schemas/v2/annotation_transfer.schema.json`. Transfer requires identical document, event, lens, source hash, raw span, quote, source context and speaker turn. All quality gates survive, including B01's foreign-speaker exclusion and B05-R1's W1 exclusion. A transfer creates no new judgment or vote. Six original defective-span annotations have changed evidence and require review on the new version; no automatic label transfer occurs. The six reviewed manual windows retain their exact evidence, including B07's connected sentences.

All annotation tasks remain blank; transfer records are separate from human-label columns. Scope insufficiency, actor mismatch, extraction boundaries and language review are separate quality flags. They do not become political ambiguity or model uncertainty. No model uncertainty was estimated.

## Counts and audit

| Actor | Original v1 candidates | V2 candidates |
| --- | ---: | ---: |
| USA | 69 | 69 |
| EU | 32 | 31 |
| Türkiye | 42 | 41 |
| India | 14 | 14 |
| South Africa | 27 | 24 |
| Total | 184 | 179 |

The six manual v1.1 revisions remain in history in addition to the 184 original candidates. V2 has 162 distinct passage groups, 179 lens records and the same ten events. PDF candidate/lens records change from 115 to 110; HTML remains 69. Counts reflect sentence merging, splitting, keyword matching and retention of reviewed windows, not a gain/loss of official documents or events.

A 22-record assistant diagnostic audit covers both documents per actor, English and French, plus both header-crossing candidates. It checks source alignment, continuation and provenance, and assigns no stance labels. It is not a random quality estimate or independent linguistic evaluation. Per-document findings are in `annotations/v2/sample_audit_summary.json`; full private details retain the reviewed text.

Remaining issues:
- Three interrupted HTML utterances retain extraction-boundary flags; sixteen foreign-speaker/reporter candidate pairs retain attribution holds. These counts overlap.
- Two raw candidate envelopes contain page headers. Their mapped reading views preserve complete sentences, and raw evidence remains exact.
- PDF intra-word spacing such as India’s `continue s` / `Th ose` and Türkiye’s `settlemen t` / `regi on` remains unchanged. Visual source comparison is still required to decide whether individual artefacts reflect PDF extraction or published text. No speculative correction enters evidence.
- French requires language review. Turkish English attachments are unofficial/courtesy translations, with originals and translator provenance unavailable. No machine translation was made.
- EU institutional representation is documented, but common-position eligibility still needs corroboration. Source-rights review remains open. Sentence completeness does not clear policy scope, attribution or scoring eligibility.

## Outputs and review

Private outputs: `/workspace/orbit-observatory/.local/annotation-v2/` contains `candidates.json`, `segments.json`, `lineage.json`, `annotation_transfers.json`, `queue.csv/jsonl`, `sample_audit.json`, `report.json`, `manifest.json` and `next_five.csv/jsonl`. Metadata/configuration and the new batch-to-candidate mapping are in `annotations/v2/`. The original v1 queue, first batch, sources and review ledgers retain their prior hashes. New artifacts are deterministic, refuse conflicting immutable history, and refuse overwriting label-bearing exports.

`V2-B01` through `V2-B05` are the next five tasks, one per actor/lens. These IDs do not reuse B11–B25 from the original batch. Their exact central passages have complete boundaries; language, translation and substantive scope still need review. Read the exact passage with context against the complete proposition. Use `support`, `oppose`, `no_stance`, `mixed`, `unresolved`, or defer language review with an empty label and a note. Return `V2-B01 | label | reasoning` in chat, stating whether review remains AI-assisted/non-independent. Do not infer a stance from keyword retrieval. French can be deferred.

Cache retention has been observed in this attached workspace, including this task. It is not a guarantee for a fresh machine. Ignored `.local/` files are not in Git. Keep source/excerpt artifacts in permitted private storage with this version’s manifest and the original pilot’s raw/text/cache files. No public redistribution or storage upload is authorized by this task. If private backup is unavailable, use the documented permitted retrieval route, require identical raw/text hashes, then run this command. A hash mismatch requires a new source version and review rather than reusing offsets or judgments. See ANNOTATION_REVIEW.md for the existing rights and backup limits.
