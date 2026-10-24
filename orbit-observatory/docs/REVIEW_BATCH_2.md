# Fourth reviewed return and next ten tasks

23 October 2026. Run from `/workspace/orbit-observatory/orbit-observatory`:

    PYTHONPATH=python python -m orbit_data.review4
    PYTHONPATH=python python -m unittest discover -s tests -v

The command reuses cached text and existing segmentation. It neither recollects documents nor regenerates the 179-candidate queue. It records/verifies review-0004 and prepares/verifies a separate ten-task batch.

## Recorded judgments and quality

V2-B01 support; V2-B02 no_stance; V2-B03 no_stance; V2-B04 no_stance; V2-B05 unresolved. The supplied reasoning is preserved verbatim in review_notes. All five use annotation schema 1.2.0, with origin ai_assisted_reviewed, Badr_A, reviewed_non_independent and independent_human=false. The public metadata ledger is annotations/v2/reviews/Badr_A/review-0004.review.json; it links to review-0003's hash.

Stance labels remain separate from eligibility and evidence quality. A new schema, schemas/review-v1/quality_assessment.schema.json, validates separate quality-assessment sidecars without changing frozen annotation/claim schemas or rewriting candidate flags. V2-B02 records assisted French review and retains language review plus EU common-position eligibility flags. V2-B03 retains the unofficial-translation qualification. V2-B05 adds scope_insufficiency and directional_scoring_eligible=false: territorial-integrity language is partial evidence and does not establish the complete strict target, including annexation non-recognition. No political/model ambiguity is inferred. All five annotations remain unscored; other source gates are not cleared.

The original blank task exports, all source text and flags remain unchanged. Returned task copies live separately under the private annotation-v2/reviews/Badr_A/review-0004 directory. Their portable review_status uses needs_adjudication because the original task schema has no reviewed_non_independent status; the canonical annotation ledger carries the precise reviewed provenance. No independent annotator is invented.

## Counts

| Counting basis | Support | No stance | Unresolved | Total |
| --- | ---: | ---: | ---: | ---: |
| All historical decisions | 6 | 8 | 7 | 21 |
| Latest judgment per review family | 5 | 7 | 3 | 15 |

Opposition, mixed and inapplicable counts are zero. Twelve families have resolved stance labels; five have a support/opposition direction label. These counts are not claims of scoring eligibility. Manual revision chains and exact-evidence transfer aliases are counted once; distinct lenses remain separate tasks. See review-0004.summary.json for the counting policy and unresolved IDs.

The three current unresolved judgments are B09-R1, B10-R1 and V2-B05, all for strict territorial-recognition scope insufficiency. Earlier defective-span unresolved decisions remain in history but have reviewed successors. Separately, B05-R1 retains support with the W1 scope hold and exclusion. B01's no_stance retains its speaker-attribution exclusion. Source/language/translation and EU common-position holds remain independent of these labels. Independent judgments: zero. Directionally scored claims: zero.

## Next ten and preserved controls

Private portable exports: `/workspace/orbit-observatory/.local/annotation-v2/batch-0002/next_ten.csv` and `next_ten.jsonl`. The same directory contains control_records.json, control_lineage.json, original_controls.json and manifest.json. Public metadata mapping: annotations/v2/batch-0002/manifest.json. All ten response fields are blank, with no suggested labels.

V2-B06–V2-B10 are five unreviewed retrieved candidates, one per actor. V2-B11–V2-B15 preserve the original B21–B25 actor-stratified random controls, sampled with seed 20261023 and their original lens assignment. There was no new random draw. The original controls and original first batch remain untouched and their hashes checked.

Four original PDF controls were physical-line fragments. Their new windows are the smallest complete source-aligned sentence envelopes containing the sampled line. The USA HTML control is unchanged. Every control keeps document/event/lens/text identity and original-to-new offsets in a separate lineage record. The original control task IDs were not canonical claim records, so they are linked in control_lineage.json, not inserted as fictitious claim parents. Five new claim-schema-2.0.0 control records validate their evidence; they remain separate from the 179 retrieved candidates. No annotation was transferred.

All five expanded central windows still have no keyword match for their assigned lens under the frozen language-specific retrieval rules. Surrounding context can include retrieved material; assess the central passage with context without treating an adjacent stance as an automatic central claim. Expansion changes the sampling unit, so this is a diagnostic continuation of the original line-based controls, not a new random sample of complete sentences or a recall estimate. Original seed/populations and offsets remain auditable. The India control retains the printed line-ending hyphen in independent-minded, without speculative text correction.

Read the exact proposition, central passage and context. Actor metadata identifies the target actor; verify the speaker and any quoted attribution. Record support, oppose, no_stance, mixed or unresolved with reasoning. Use not_applicable only for a genuine temporal exclusion. Return V2-B06 | label | reasoning through V2-B15 in chat, stating whether assistance/provenance remains the same. Source URL, issuer, dates, language, exact offsets and sufficient original context are preserved in the portable files. Unofficial/courtesy translation and EU eligibility qualifications remain visible in the source review and claim metadata.

## Validation and limits

All 48 focused checks pass. Live validation covers 415 canonical records including five controls, plus the five separately validated quality assessments. CSV/JSONL exports reproduce exact source offsets/context and resolve their document/event/lens references. Repeated execution preserves artifact bytes; label-bearing returned files are never overwritten. Existing v1/v2 manifests and the review ledger chain remain intact.

The French review is explicitly assisted, not independent language validation. Turkish originals/translator verification, EU common-position eligibility, source-rights review and remaining extraction flags elsewhere in the queue stay open. All cached full text/excerpts remain private under ignored .local; retention on a fresh machine is not guaranteed. No collection, training, score change or website-design change occurred.
