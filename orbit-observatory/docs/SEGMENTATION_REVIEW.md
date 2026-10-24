# PDF boundary audit and second assisted review

Current resolution: W1 selected and source-aligned v2 implemented. See [SEGMENTATION_V2.md](SEGMENTATION_V2.md) and codebooks/v1.0.2/decision.json. The audit and pending-choice discussion below describe the preceding historical checkpoint.

## Recorded judgments and history

Review review-0002 preserves six user-supplied AI-assisted decisions reviewed by Badr_A, all explicitly non-independent: B05-R1 support, B06 support, B07 unresolved, B08 no_stance, B09 unresolved and B10 unresolved. The exact reasoning is in annotations/v1/reviews/Badr_A/submission-0002.json and canonical review_notes in review-0002.review.json. Annotation schema 1.2.0 is reused unchanged; no extra schema version was needed.

The first review, original B05 unresolved decision, first blank batch, source-quality/speaker audits, raw files and frozen candidate offsets remain intact. Review-0002 links to the previous ledger hash. B05-R1's support is recorded on that repaired candidate, not on the original fragment, and remains blocked by the separate scope conflict. B06's support and B08's no_stance remain on their original fragment versions; neither is transferred to a repaired version. Five new tasks remain entirely unlabeled. There are eleven assisted-reviewed decisions, zero independent annotations and no computed scores.

Private current artifacts are under the outer .local/annotation-v1/reviews/Badr_A/review-0002/: overlay_records.json, revisions.json, repaired_tasks.json, revision_metadata.json, reviewed_first_batch.csv/jsonl and reviewed_B05-R1.task.json. Versioned ledgers and audit metadata contain references/qualifications rather than full source text. The earlier private archive predates these reviews and was not overwritten.

## Root cause

The path is python/orbit_data/collect.py PDF extraction -> python/orbit_data/text.py normalize -> candidate_spans. pypdf returns physical layout line breaks. orbit-text-v1 deliberately preserves LF boundaries for reproducible offsets. candidate_spans then searches each newline-separated unit independently, previously calling it a paragraph. A PDF layout line is neither a semantic paragraph nor a complete sentence. Keyword retrieval therefore frequently selects a middle line rather than the full claim.

The frozen v1 function's documentation now names that limitation correctly. Its output behavior has not changed. Joining/reflowing text or changing candidate_spans in place would invalidate source hashes, evidence offsets and existing decisions, so this task did neither.

## Audit coverage and limits

annotations/v1/reviews/Badr_A/review-0002.boundary_audit.json audits all 184 original candidate/lens pairs and all six current span revisions, not just the first batch.

| Group | Audited | Flagged for review |
| --- | ---: | ---: |
| Original PDF pairs | 115 | 114 |
| Original HTML pairs | 69 | 3 |
| All original pairs | 184 | 117 |
| Existing/new repaired spans | 6 | 0 |

The 117 flagged pairs represent 115 distinct source spans; cross-lens copies are not new events. Flags check possible missing sentence starts/ends and retained header material, with conservative abbreviation/page-header handling. They assign no stance or eligibility label and do not overwrite any record. Zero flags does not certify an atomic or attributable claim: context, legal scope, negation, language and institutional mandate still require review. False positives and missed problems are possible.

Next segmentation work should be a separately versioned, source-aligned proposal: segment across layout line wraps; mask headers only in an auxiliary view of equal indexed length; respect speaker changes, quotations and language-specific punctuation/abbreviations; map every proposed span back to exact original Unicode offsets. Sentence completeness alone is insufficient, so antecedent/attribution context may need a larger window or reviewed atomic child spans. Test on the audited examples and compare against v1 before approving new units. Do not regenerate/relabel the 184 annotated-corpus candidates or present another batch as though this problem were solved. Only the five explicitly requested repairs were created here.

## Repaired spans pending Badr's review

| Task | Original offsets | Expanded offsets | Qualification |
| --- | --- | --- | --- |
| B06-R1 | [3161, 3228) | [3132, 3228) | Full sanctions sentence; EU common-position gate remains |
| B07-R1 | [2998, 3080) | [2567, 3228) | Multiple contiguous sentences identify Ukraine/aggression and the Kremlin while retaining the original evidence; overlaps B06-R1 within the same event |
| B08-R1 | [3017, 3063) | [2959, 3063) | Full French sentence; no translation or text change |
| B09-R1 | [4832, 4897) | [4760, 4922) | English PDF explicitly marked UNOFFICIAL TRANSLATION; Turkish original not collected |
| B10-R1 | [5990, 6059) | [5916, 6070) | English PDF marked Courtesy Translation / Check against delivery; Turkish original not collected |

Each new claim uses the existing revision schema 1.1.0, with revision_of pointing to its original candidate, the same document/event/lens/text hash, a review-request reason/requester and a distinct ID. Tasks use revision-task schema 1.1.0. Validation checks strict expansion, exact substring/context integrity and no inherited label. The five originals and their submitted judgments remain present. Revisions do not add communication events.

## Scope clarification and pending decision

See codebooks/v1.0.1/SCOPE_CLARIFICATION.md and status.json. Frozen codebook 1.0.0 and configured target definitions were not changed. Equivalent explicit comprehensive scope can meet the withdrawal target without the literal words “all” or “1991.” Unqualified “Ukrainian territory” leaves that legal extent implicit, so the current strict reading does not automatically admit B05-R1 to exact-target scoring. Its submitted support remains saved, and review-0002.scope_conflict.json has resolution=null and blocked_scope_conflict.

The pending substantive choice is W1 (retain strict comprehensive-scope evidence) versus W2 (approve an explicit, versioned inference convention accepting unqualified withdrawal without stated exceptions). W2 can change coverage and aggregate positions and requires new protocol/versioned review and sensitivity reporting. It does not automatically broaden territorial recognition. Ukraine-specific territorial-integrity language alone still does not explicitly settle all recognized borders/annexation; any broader target would need separate approval and a new series. No proposal has been adopted or applied.

## Validation

From /workspace/orbit-observatory/orbit-observatory:

    PYTHONPATH=python python -m orbit_data.followup
    PYTHONPATH=python python -m unittest discover -s tests -v

The recording command is idempotent for the exact saved submission and checks its existing artifact hashes. Validation combines the unchanged 204-record corpus with six linked revisions and eleven annotations: 221 unique records. All raw/text hashes, offsets, parent containment, event identity, source-language/translation qualifications and blank follow-up response fields were checked. The original batch/queue artifact hashes and prior ledger bytes were verified unchanged. All 33 tests passed. No collection, training, public-score or website change occurred.
