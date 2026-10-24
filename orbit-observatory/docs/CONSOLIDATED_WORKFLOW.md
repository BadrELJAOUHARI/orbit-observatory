# Consolidated pilot workflow

23 October 2026. This replaces small batch handoffs. Original batches, judgments, source files, audit flags and revision links are preserved. The previous operation is complete; pending V2-B06–V2-B15 tasks are now part of the consolidated queue, not a request to finish another small batch.

## Pilot findings

Ten official documents and ten events, two per actor, produced a frozen 184-candidate legacy queue. Source-aligned reconstruction produced 179 candidate/lens records; five preserved seeded controls bring the current worklist to 184. These are different versions/populations, not an increase in independent evidence. Candidate retrieval is broad: Russian military operations, NATO deployments, other conflicts and generic sovereignty frequently match keywords without establishing the exact target. The pilot cannot establish annual policy coverage or classifier accuracy.

The 21 historical assisted decisions collapse into 15 current review families: five support, seven no_stance and three unresolved. All three unresolved cases concern strict recognition scope. B05-R1 separately retains support behind its W1 exclusion. No independent annotation or directionally scored claim exists. Existing sources/annotations are unchanged.

The new deterministic screen finds 90 mechanically clean records and quarantines 94. Counts overlap by reason: 32 EU common-position flags, 42 translation flags, 12 French language flags, 16 speaker flags, three interrupted HTML utterances and seven suspected intra-word-spacing cases in evidence or supplied context. Source eligibility is a separate dimension from stance. Mechanically clean does not mean cleared for public scoring.

Two page-header obstructions are resolved through the existing exact source-index reading map. The raw envelopes and original flags survive; the resolution is a new sidecar. Header templates must match complete physical lines. Interrupted utterances and suspect spelling/spacing are not repaired by guessing. Quarantine logs include source offsets of suspect words for private PDF comparison. Earlier complete-sentence segmentation and control repairs are reused; no source text or candidate ID is overwritten. Rights and cache limits remain as in ANNOTATION_REVIEW.md.

## One AI pass and one review queue

The consolidated rule reference is [codebooks/consolidated-v1/README.md](../codebooks/consolidated-v1/README.md). All five targets and W1 remain unchanged.

One assistant contextual pass supplies 84 draft suggestions for all clean, currently unreviewed candidates: 15 support, 64 no_stance and five unresolved. There are no suggested opposition or mixed cases in this small clean pilot. Do not invent them or infer that the actors never express them. The five unresolved suggestions concern four partial-scope passages and one sanctions-effect-versus-endorsement passage. These are draft categories, not new Badr_A judgments or calibrated uncertainty.

Suggestions use schemas/suggestions-v1/suggestion.schema.json, with AI origin, unreviewed status, null annotator/probability, independent_human=false and training/scoring approval false. The private frozen decision map records the input/context fingerprint, prompt, method and rationales. Reproduction replays this saved map; it does not pretend to re-run a deterministic language model or call repeated models as independent annotators. workflow/v1/pass_manifest.json records its hash. Preserve the private map with the source cache for future-machine replay.

Private outputs under `/workspace/orbit-observatory/.local/workflow-v1/`:

| File | Purpose |
| --- | --- |
| review.html; review_queue.csv/json | All 184 items, prioritized source/attribution/text problems, scope, opposition/mixed if present, ambiguity, routine checks. Existing judgments are read-only; human fields are blank. |
| blind_evaluation.html/csv/json | Separate 21-item evidence-only labeling rehearsal from five reserved events. No suggestions, prior labels, AI rationales, review priorities or assistant quality hints are embedded. Published source qualifications remain. |
| quality_screen.json; quarantine.json | Original/effective flags, mapped-header resolutions and unresolved text/source problems, without stance relabeling. |
| evidence_ledger.json | Source/event/offset links, controls, provenance links, exclusions, null real weights/contributions/scores. |
| coverage.json | All 25 actor/lens combinations, collection versus retrieval versus review/AI/quarantine counts, temporal applicability and unscored coverage. |
| sealed/draft_pass.json; sealed/all_suggestions.json | Complete frozen AI pass, including reserved-event drafts. Keep away from blind annotators. |
| development_suggestions.json | The 21 suggestions visible in development review. |
| training_preflight.json | Blocking label/source/split/dependency prerequisites. No fitting occurred. |
| SYNTHETIC_aggregation_fixture.json | Clearly labeled arithmetic fixture; never a real score. |
| report.json; manifest.json | Counts and reproducibility hashes. |

Evaluation reservation seals 63 of the 84 suggestions for entire held-out events, not only the 21 selected passages. They are not embedded in review HTML/CSV or training inputs. The remaining 21 suggestions are visible. The consolidated queue keeps reserved evidence but disables labeling it there; use the separate blind file. This preserves one worklist while avoiding suggestion exposure for the separate evaluation exercise. Physical files are not access-controlled vaults: assign blind annotators only their blind files, not sealed files or the existing assisted ledgers.

All five original retrieval controls survive, retain their selection status and original seed/offset lineage, and are included in the consolidated queue. Where their events are reserved, they also appear in the blind packet. Their expanded central passages remain non-retrieved for their assigned lens. They are diagnostic controls, not an unbiased sentence sample or a recall estimate.

## Remaining decisions and clearances

| Topic | Current binding rule or hold | Remaining decision/action |
| --- | --- | --- |
| Exact territorial scope | W1 and complete territorial-recognition target retained; no broader inference adopted | Adjudicate partial wording under these unchanged targets. B05-R1 support stays excluded; preserve its submitted label. |
| EU institutional evidence | Representation verified; common-position gate unresolved | Corroborate common institutional endorsement or keep affected speech evidence quarantined. |
| Translation/language | French assisted review is not independent validation; Turkish versions are unofficial/courtesy translations | Arrange qualified review and original/authorized-version corroboration, or explicitly approve a separately qualified research-only stream. No gate is cleared by default. |
| Sanctions effects and endorsement | Reporting effects alone does not automatically endorse policy | Decide whether the specific “our actions” passage constitutes endorsement in context; also review negation/hypothetical-effect cases together. |
| Confirmatory evaluation | Pilot events already informed codebook development | Reserve untouched additional events and separate independent humans. Current event-grouped export is rehearsal only. |
| Class/coverage sufficiency | No clean opposition/mixed examples and inadequate annual coverage | Expand genuine official-source coverage and class representation before claiming five-lens model validation; do not fabricate balance or relax targets. |

Word-spacing/source-image comparison is a mechanical clearance task rather than a proposal to redefine a lens. The consolidated queue identifies the affected records; they remain quarantined until a traceable correction or documented source qualification is recorded.

## Review and return without batch handoffs

Open review.html locally. Filter by actor, lens, quarantine reason or priority; read the exact passage, source-aligned aid and context. Enter your label, annotator ID and brief reasoning. The separate source-eligibility, text-quality, attribution and scope controls record quality decisions without changing stance labels. Quality-only returns are supported and saved as separate append-only sidecars. Click Export responses as CSV before closing; edits are not remotely submitted or automatically saved. Reviewing this file is assisted and non-independent. Leave labels blank and explain deferrals in notes where source/text problems remain.

From `/workspace/orbit-observatory/orbit-observatory`:

    PYTHONPATH=python python -m orbit_data.workflow
    PYTHONPATH=python python -m orbit_data.training
    PYTHONPATH=python python -m unittest discover -s tests -v
    PYTHONPATH=python python -m orbit_data.review_import /path/to/returned.csv --review-id bulk-review-0001

The importer protects all evidence, flags, existing labels and suggestions, and imports only human response fields into a new private append-only review ledger. It does not clear source gates or approve training. Returning a partially completed full queue is allowed; unlabeled notes remain recorded as deferrals. Do not edit immutable baseline files or regenerate a label-bearing return over an existing review ID.

For blind rehearsal, give each independent person a fresh copy of only the blind export. They label separately, confirm no suggestion/prior-label exposure, and return separate CSVs with distinct annotator IDs. Import with --blind and a separate review ID. Existing assisted event exposure disqualifies that annotator from independent status on the same event. Different annotators' judgments remain separate records; only corrections by the same annotator supersede their own record. The importer validates claims but cannot verify a person's truthful exposure declaration. Prior pilot/codebook exposure means this remains rehearsal, not a final test set.

## Independent implementation and completion criteria

The hierarchy engine gives distinct eligible canonical claims equal shares within events, events equal shares within quarters, and observed covered quarters equal shares of the window. It rejects AI drafts and unapproved outputs, inconsistent duplicates/dates, mixed streams and unintended fixtures. Its contribution ledger sums exactly to the observed-window estimate. Full-year publication requires all four quarters and at least two eligible events on distinct dates per quarter, the methodology's provisional gate. Missing years stay null. Current real evidence ledgers have null scores/weights; only explicitly synthetic arithmetic fixtures have values.

Training setup includes guarded TF-IDF/logistic-regression and pretrained-transformer adapters, event-disjoint development splitting and sealed evaluation exclusion. Preflight is the default. All 21 assisted records are rejected as training data under the initial strict human-label policy; zero current rows are approved. Scikit-learn 1.8.0 is available; optional baseline pins are in requirements-training-baseline.txt. Torch/transformers are not installed, model revision is unpinned and compute readiness is untested. The transformer adapter has not executed or downloaded weights. Neither baseline nor transformer was fitted. Source/language clearance and event-disjoint calibration data are still prerequisites.

Annotation is complete for a release dataset when every included record has exact, reproducible evidence; resolved actor/source/language eligibility; adjudicated target-specific labels; documented exclusions; reviewed retrieval controls; and genuinely independent double coding for the evaluation/gold subset. Start toward the methodology's roughly 200 double-coded claims, report agreement/confusions and expand where class/actor/lens coverage fails. This planning budget is not a validity or training-size guarantee. AI suggestions alone never satisfy these criteria.

Training is complete only after approved event-disjoint data and genuine class coverage exist, dependencies/model revision/compute are fixed, baseline and transformer runs execute reproducibly with saved checkpoints/configuration/data hashes, and calibration uses development events only. Existing assisted labels cannot enter the current strict training policy without a separately versioned approval/policy decision. No automatic fitting happens when a review CSV is imported.

Evaluation is complete only after codebook/model/calibration/thresholds are frozen, untouched event/time holdouts have two independent judgments and adjudication, no event/copy/translation crosses splits, and held-out macro-F1, per-class/actor/lens errors, calibration and aggregate-score error are reported with coverage and uncertainty. Compare with the baseline; freeze release thresholds before opening final labels. Unsupported classes/cells remain explicitly unvalidated. Rehearsal and assisted labels do not count as confirmatory gold.

Next milestone: bulk adjudication/source clearance and collection of untouched evaluation events, followed by an approved training-data freeze and baseline readiness check. No further small annotation batches. Current public design and editorial scores remain unchanged until validated replacements and coverage gates pass.

## Verification for this implementation

All 59 focused tests pass, including unequal claim/event/quarter weighting, mirror deduplication, duplicate-score conflicts, distinct-date coverage gates, AI/fixture rejection, mapped header resolution without source edits, suspect-word quarantine, blind split leakage, provenance contracts and protected/quality-only CSV returns.

Chromium exercised 184 review rows, 21 visible development suggestions, filtering, edited CSV export and importer validation, plus 21 blind rows with no embedded AI/history and zero page errors. Only synthetic UI responses were written to /tmp; they were never imported as annotations. A second workflow build reproduced every output byte. Frozen v1/v2 manifests, the 21 historical judgments and source hashes validated unchanged. Current real ledgers have only null scores/weights/contributions; the arithmetic example is explicitly synthetic and not publishable.
