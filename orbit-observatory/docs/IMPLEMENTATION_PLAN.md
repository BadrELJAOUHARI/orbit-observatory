# ORBIT implementation plan

Status: acquisition sprint completed with 561 new clean development pairs / 255 event records / 238 leakage groups (189 pairs from focal actors; 372 auxiliary UK). The 1,000-pair stretch goal remains unmet; India/Türkiye access and exact-scope coverage remain gaps. All 113 completed reviews and 38 eligible examples / eight events are unchanged. New suggestions are unreviewed and unauthorized for training. See ACQUISITION_SPRINT.md.
Updated: 24 October 2026.

Authority: AGENTS.md and HANDOFF.md establish scope; ORBIT_Methodology_v0_1.qmd supplies measurement details. The handoff supersedes the methodology's older two-actor, first-lens-only release wording. Stages below are development increments, not reduced release scope. The current milestone adds configurations, schemas and collection, without model training or public-score changes.

## Release contract

- Universe: Russia–Ukraine. Tracked actors: United States, European Union, Türkiye, India, South Africa. Russia and Ukraine are fixed policy reference poles.
- Lenses: territorial recognition, Russian troop withdrawal, military assistance to Ukraine, sanctions against Russia, responsibility for the February 2022 full-scale invasion. Responsibility is inapplicable before the invasion, including earlier 2022 statements.
- Timeline: 2012–2026 where evidence permits; explicit nulls, coverage dates and partial-year cutoff. No interpolation or invented movement.
- Preserve logo, landing page, central 3D scene, black holes, planets, timeline, controls, compact labels, hover details and dossier styling. Extend the existing editable dist/ sources rather than replace the design.
- Required release capabilities include provenance, reviewed claims, baseline and fine-tuned transformer, evaluation and calibration, auditable hierarchical scoring, uncertainty, all actor/lens filters, period comparison, sensitivity controls and an advanced profile/composite view.

## Current checkpoint

The app is plain JavaScript with bundled Three.js and legacy Python standard-library scripts. dist/ is source, not disposable build output. Its six selected official-source records cover USA/EU in 2014, 2022, 2024 and 2025; one full transcript is local. Every public score is editorial +1. Aggregation is a document mean, not the approved hierarchy. The existing general sovereignty lens must not be relabeled as validated territorial recognition without reviewing its evidence.

The research pipeline retains ten pilot events plus 43 additional focal and three auxiliary events, with source hashes and event-grouped evaluation reservations. The 68 checked return decisions are appended with Badr_A, assistance, reported extra checks and non-independent provenance. The expanded development packet is now an archive of 113 completed/history records: 68 preserved reviews and 45 newly imported, human-checked assisted judgments. Twelve new records were mechanically clean; ten pass the complete supervised-data gates. Fifty-one new policy-screened passage-lens pairs and 41 rejected retrieval pairs are distinguishable. Source/quality holds, labels, suggestions and predictions remain separate. Broad speeches are supplementary acquisition; targeted searches are explicitly training acquisition, unsuitable for representative annual scores.

Current completion criteria:
- Annotation: consolidated review/adjudication, exact evidence references and explicit source/scope decisions; retain assistance and independence flags. Approve any territorial component revision before applying it. W1 remains fixed.
- Training: approved, source-cleared genuine classes on event-disjoint training/development data; 113 reviewed records have conditional authorization, 89 have resolved target labels, and 38 pass all evidence gates. Sanctions/responsibility have completed exploratory grouped baselines; the other lenses retain precise class/event blockers. Two real-data exploratory baselines already ran; do not rerun unchanged experiments. Versioned training policy 3.0.0 retains the 113 record-scoped grants, actual assistance/check provenance and blind-independent=false; source/text/scope gates remain binding.
- Evaluation: untouched grouped event/time sample, two genuine independent human judgments, agreement/adjudication, no AI suggestions or tuning leakage, separate calibration events. Current reserved events are unlabeled; no final metrics are claimed.
- Publication: validated classifier/calibration, coverage, hierarchical ledger and uncertainty gates. Preserve current editorial scores and scene until replacements pass all gates.

Next single milestone: return one consolidated review of the new clean evidence, while obtaining a permitted official-source discovery/rendering route for undercovered India/Türkiye and genuine contrast examples. C24-M1 stays pending without blocking collection. Train only after approved eligible data materially expands, under unchanged event-group validation. Territorial-component changes remain unapproved; W1 is unchanged.

## 1. Establish versioned contracts and reproducible tooling

Implemented for actors, lenses and the five record types requested in this milestone. Aggregate/release schemas remain for stages 4 and 8. Pilot institution definitions still need human review; they are explicit configuration, not a validated codebook.

Define Python project layout, pinned dependencies and commands only when required by implemented functionality. Version actor scopes, lens definitions, source manifests, schemas and weighting settings. Retain the current static serving workflow.

Acceptance:
- All five actors and lenses have stable IDs and explicit eligibility, orientation, temporal scope and qualification rules.
- US executive and EU common-position scopes follow the methodology. Define comparable authorized executive/diplomatic sources for Türkiye, India and South Africa before collection; do not silently mix institutional streams or EU member states.
- Separate records for document, event, claim, prediction/review, aggregate and release include the methodology's required fields. Document/event dates differ from retrieval dates.
- Validation rejects invalid offsets, unknown IDs, duplicate identities and scores without provenance. Small fixtures are explicitly synthetic test data and never published as research observations.

## 2. Collect and audit a small official-source pilot

Collection pilot implemented: two documents per actor, with raw/text hashes, normalized text, provenance and cached repeatability. EU UN statements replaced robot-disallowed Consilium URLs; one is French. Source review verified official actor/role/stated dates, but EU common-position eligibility remains pending despite verified EU delegation representation. Turkish attachments are marked unofficial/courtesy translation, now recorded correctly. Candidate selection is not annotation. Full retrieval recall, source-rights review and event/scope adjudication remain open. Actual sources contain no detected exact duplicates; synthetic checks cover copy/translation behavior. Retention is verified in the attached workspace; a private verified archive was prepared, with fresh-machine cloud restoration explicitly untested.

Start with a bounded stratified sample across all five actors and lenses, then expand. Review source access terms; cache permitted documents, use respectful request rates, and record failures instead of silently dropping them. Preserve canonical URL, issuer/institution, event/publication dates, UTC retrieval timestamp, language, translation provenance, text hash and permitted snapshot location.

Acceptance:
- Repeat collection reuses cached material and stable IDs. Retries, inaccessible pages and archive gaps have an audit log.
- Mirrors, translations, excerpts and syndicated joint statements cluster into communication events. Preserve each actor's explicit endorsement; linked events remain together in dataset splits.
- Original text and character offsets reproduce every evidence span. Existing curated records are retained as legacy editorial material until re-reviewed.
- A manual retrieval/attribution audit measures missed relevant material and speaker errors. Public availability is never described as collection completeness.

## 3. Build the annotation codebook and reviewed corpus

Preparation completed: frozen common and five-lens codebooks 1.0.0; separate strict task schema; mixed-capable annotation record schema 1.1.0 preserving the old contract; 184 portable tasks with exact text/context and cross-lens passage groups; first 20 retrieved candidates spanning every actor/lens/document plus five seeded actor-stratified non-retrieved controls. See ANNOTATION_REVIEW.md. The original preparation files remain unlabeled; independent pairs still do not exist. French-original review and Turkish translation corroboration remain explicit gates; no machine translation or suggested labels are supplied.

Follow-up: five user-supplied AI-assisted judgments reviewed by Badr_A are now stored using specialized schema 1.2.0, explicitly non-independent. They are not independent gold annotations. Original B05's unresolved decision is preserved; a complete-sentence revision awaits a new judgment. A speaker audit flags additional US wrong-speaker/question candidates without labeling them. REVIEWED_JUDGMENTS.md records provenance, append-only history and validation.

Historical second follow-up (resolved by the v2 checkpoint below): six additional assisted judgments are recorded without replacing previous ones. B05-R1 support remains behind an explicit protocol-scope conflict. B06–B10 have linked sentence/context revisions pending review, with French and translation provenance intact. The boundary screen flagged 117/184 original candidate/lens pairs, including 114/115 PDF pairs; do not treat physical PDF lines as claims. See SEGMENTATION_REVIEW.md and codebooks/v1.0.1/ for the unadopted scope proposal. Sentence segmentation and source-aligned context/attribution repair must be validated before another batch; mass relabeling/replacement is prohibited.

A claim is a source passage expressing an attributable position on an exact policy question. Separate support, opposition, no stance, unresolved attribution/meaning and inapplicability. Preserve qualifications; peace talks or generic sovereignty language alone do not establish a territorial position.

Acceptance:
- Pilot roughly 200 independently double-coded claims, stratified across actors, lenses, periods and difficult cases. Report agreement, confusion and adjudication; revise codebooks with version history.
- Aim toward 600–1,000 labels if feasible, guided by class coverage and learning curves rather than assuming these budgets guarantee adequacy.
- Review tooling exports genuine offsets, context, annotator decisions and correction history. Repeated identical claims within one event do not gain additional weight.
- Freeze event-grouped development, calibration and final later-period test partitions before modeling. Translations, joint statements and mirrors never leak across them. Calibration/main evaluation use representative samples or documented sampling weights.

## 4. Implement the measurement engine and evidence ledger

Develop deterministic scoring independently of model training, using explicitly labeled fixtures or reviewed labels. For eligible stance-bearing claim i, calibrated support probability p_i gives s_i = 2*p_i - 1. An event score s_e is the mean of its m_e distinct eligible claims. With Q covered quarters and n_q eligible events in quarter q:

    a_e = 1 / (Q * n_q)
    S = sum(a_e * s_e)
    contribution_i = a_e * s_i / m_e

Acceptance:
- Contributions sum to S; eligible event weights sum to one; each covered quarter has equal budget. Duplicating a mirror or repeating an identical claim leaves the score unchanged.
- Ledger exports every eligibility decision, claim/event/quarter weight and contribution. Exclusion recalculates the complete hierarchy. No additional confidence, document-length, prestige or GDP multiplier.
- Full-year publication provisionally requires all four quarters with at least two eligible events on distinct dates in each. Failed coverage produces a clearly bounded provisional window or null, never a complete-year claim. Publish counts and effective event count 1/sum(a_e^2).
- Separate no stance, unresolved evidence, missing coverage and not applicable. Show an exact 2026 cutoff and compare matching windows; define completed-quarter versus partial-quarter rules explicitly.
- Single-lens distances are d_U=(1-S)/2 and d_R=(1+S)/2. Current x=6*S with anchors at +/-9 does not share that normalized axis. Choose and document an analytical axis separate from decorative margins, or reconcile coordinates without changing the visual identity. Perpendicular offsets, planet sizes and camera perspective carry no stance meaning.

## 5. Train and evaluate later, after data readiness

Start with a simple text classifier baseline, then fine-tune a pretrained transformer. A transformer already learned language patterns; fine-tuning adapts it to the reviewed policy labels. Neither is trained during this setup task.

Before training, inventory CPU/GPU, RAM, disk, pretrained-model license/access and label balance. Select model size, batching, seed and artifact paths from those resources; preserve datasets and checkpoints for reuse. Do not promise a training result before this assessment.

Acceptance:
- Attribution/relevance gates and abstention thresholds are selected on validation data. Irrelevant text cannot become a midpoint stance by renormalizing tiny class probabilities.
- Compare baseline and transformer on identical held-out events: per-class precision/recall, macro-F1 and errors by actor, lens, period and source.
- Calibrate probabilities on a separate partition. Calibration means checking whether predicted probabilities match observed label frequencies; report Brier score, log loss and reliability plots.
- Measure aggregate absolute error and signed bias against human-coded aggregates with identical weights, including the untouched later-period test. Predeclare tolerances before final results; the methodology's MAE <=0.10 is illustrative, not an achieved or automatically approved threshold.
- Publish model/data/calibration versions, code and seeds, model card, failed subgroups and temporal-shift limitations. Inadequate results remain explicitly experimental; an editorial pilot cannot substitute for the release's validated model requirement.

## 6. Quantify uncertainty and sensitivity

Acceptance:
- Resample whole event clusters within quarters and recompute the hierarchy, initially considering 2,000 replicates after checking runtime. Label the resulting percentile range a conditional event-resampling interval. A bootstrap repeats sampling from observed events; it cannot repair missing sources.
- Keep model variation, observed event dispersion, coverage gaps and cross-lens divergence separate. Evaluate alternate model fits; do not imply independent probability draws capture systematic model errors.
- For known unresolved weight mass u and resolved contribution T, publish sensitivity bounds [T-u, T+u] with fixed intended weights and explain that unseen documents are outside those bounds.
- Compare equal-quarter/equal-event aggregation, source exclusions, human/model labels, codebook choices and alternate models. Publish settings and changes, not just attractive stable examples.

## 7. Integrate all actors and lenses into the existing interface

Acceptance:
- All five actors and all five lenses work through the current design, including missing and inapplicable states, timeline and period comparison. Uncollected combinations remain visible as gaps.
- Dossiers show source context, authentic highlights, dates, coding/model status, ledger weights, coverage, uncertainty and correction route. JSON export reproduces the displayed aggregate.
- Hover, compact labels, click dossiers, orbit/zoom/reset, actor filters, playback, reduced motion, keyboard use and mobile controls are checked. Keep before/after visual checkpoints.
- Browser integration tests check selected evidence through ledger to numeric coordinate. Local static serving remains documented; any future backend has explicit startup and readiness checks.

## 8. Add the advanced profile/composite and release reproducibly

For an explicitly labeled advanced view, define justified dimensions, fixed reference vectors and nonnegative weights summing to one. Inspect overlap, especially territorial recognition versus withdrawal. Provide weight sensitivity and a complete-panel missing-data rule; never silently redistribute missing weights.

Acceptance:
- Composite S=sum(w_k*s_k), profile distance d_a=0.5*sqrt(sum(w_k*(s_k-a_k)^2)), and divergence H=0.5*sqrt(sum(w_k*(s_k-S)^2)) are independently tested. Multidimensional distances need not sum to one; H is policy divergence, not uncertainty.
- Inapplicable pre-invasion responsibility prevents a five-lens complete-panel composite unless a separately versioned, justified series is defined.
- Release manifest pins code commit, source/corpus/codebook/model/calibration/weighting versions, timestamp and cutoff. Preserve prior releases and corrections; store large artifacts outside Git with hashes and retrieval instructions, respecting source rights.
- Publish retrieval, annotation, model and aggregate evaluation, coverage and limitations. Reproduce a release from documented commands and check all 25 actor/lens combinations without fabricating coverage. Complete required browser, measurement and evaluation checks before calling the full release ready.

## Immediate next task

B06-R1–B10-R1 are reviewed and W1 is chosen. Source-aligned segmentation v2 is implemented and checked, with append-only lineage and exact-evidence transfer records. V2-B01–V2-B05 are now reviewed. Review V2-B06–V2-B15 next, including the preserved random controls; visually inspect remaining PDF word-spacing artefacts and retain source/language/scope holds. See SEGMENTATION_V2.md. Preserve all existing annotations and use linked versions. Obtain independent human copies before agreement/gold evaluation claims. French, Turkish-original/translation, EU common-position and source-rights gates remain. No training or score integration yet.

## Segmentation v2 acceptance checkpoint

Completed: cached sentence/paragraph reconstruction, mapped reading/source offsets, exact header/body discrimination, speaker-turn preservation, immutable v1 history, 179 regenerated candidates, ten exact-evidence transfer links, 22-record diagnostic audit, blank five-item review export and 44 focused checks. New candidate and transfer schemas are versioned; existing annotation schema remains sufficient.

Still required before expanding annotation or scoring: review next five tasks, visually check residual word spacing and interrupted utterances, resolve French/Turkish language and EU common-position qualifications, and obtain separate independent human judgments. Broaden collection/retrieval evaluation only with source-rights and coverage controls. Independent evaluation and training remain later stages.

## Fourth review acceptance checkpoint

Completed: five assisted v2 judgments, separate validated eligibility/evidence/scope metadata, assisted French provenance, explicit V2-B05 strict-scope exclusion, current-family counts and ten blank tasks with preserved random controls. Forty-eight focused checks pass; original text, flags and history remain unchanged. See REVIEW_BATCH_2.md.

Next: review all ten with selection type visible; keep retrieval misses separate from stance errors and source eligibility. Continue exact-target adjudication, source/language corroboration and truly independent annotation before gold evaluation or training.

## Current completion gates and next milestone

Small annotation batches are discontinued. Historical batch checkpoints above remain audit history, not instructions to return another batch. Consolidated rules and the compact remaining-decision table are in CONSOLIDATED_WORKFLOW.md.

| Stage | Implemented now | Completion criterion before release use |
| --- | --- | --- |
| Annotation | Preserved reviewed history, 84 AI drafts, systematic quarantine, full HTML/CSV queue and protected return importer | Every included record has exact evidence, cleared source/language/actor eligibility and adjudicated exact-target labels; independent double coding/gold and retrieval-control audit documented. Roughly 200 double-coded claims is an initial planning budget, not a guarantee. |
| Training | Offline preflight, event split, guarded baseline and transformer adapters | Approved human training data with class/actor/lens coverage, no held-out events, pinned dependencies/model revision and tested compute; executed reproducible baseline and fine-tuning with saved data/model hashes/checkpoints. No automatic import-to-training path. |
| Calibration/evaluation | Five reserved events, 21 blind rehearsal items, leakage guards | Untouched event/time holdouts, two genuinely independent judgments/adjudication, frozen protocol and thresholds, calibration fitted only on development, reported macro-F1/per-class/per-actor/lens errors, Brier/calibration and aggregate error with uncertainty. Rehearsal is not a confirmatory test. |
| Aggregation/release | Tested hierarchy, duplicate handling, coverage gates and contribution ledger; real scores null | Validated calibrated outputs only; contribution/weight reconciliation, declared streams, adequate annual coverage (four quarters, two events on distinct dates each), reviewed uncertainty/sensitivity. Current website design/editorial scores persist until this passes. |

Next milestone: bulk adjudication and source clearance, plus untouched evaluation-source expansion, then an approved dataset freeze and baseline readiness check. Remaining independent work includes broader retrieval/coverage audits, transformer dependency/model pin/compute checks and eventual calibration/evaluation implementation. No model training is authorized by this workflow-preparation step.

## Development review usability checkpoint

Completed: development-only 68-record packet; no reserved event text/context; unreviewed, clean and quarantined filters; automatic local response/settings saving and honest saved status; CSV/JSON resume with conflict and immutable-field guards; backend baseline recognition; 62 Python tests plus browser reopen/export/import checks. See DEVELOPMENT_REVIEW.md.

Badr's next action is bulk review of clean records and return of the complete exported CSV. Source clearance and collection expansion remain independent technical work with new versioned artifacts, preserving the active review snapshot. Keep blind event exclusions, provenance, strict codebooks, training approval and public scoring gates unchanged. No further small batches.


## Targeted acquisition checkpoint (24 October 2026)

- Completed 54 bounded, resumable batches including cache rechecks: 1,398 source URLs, 858 stored source documents (855 new), 561 new clean pairs / 521 passages / 255 events / 238 conservative leakage groups. Focal: 189 pairs / 70 events / 62 groups; auxiliary UK: 372 / 185 / 176. Coverage spans 2014–2026 and all five lenses; new clean India/Türkiye coverage remains zero. Scope remains five displayed actors, never six.
- Relevance/source/offset/split gates precede clean export; 691 held development pairs, 51 passage rejections, 15 duplicate diagnostics and 694 new reserved records stay separate. Original bytes, source receipts, unchanged text, exact offsets and selection methods persist in the private cache checkpoint. Historical evaluation text/labels/splits remain untouched.
- One practical new-only HTML/CSV/backup packet, 526 support / 35 unresolved **rule suggestions**, zero new approved labels. Existing 113 judgments/history/authorizations are preserved rather than repeated. Official actions versus legal implementation remain identifiable. No opposition/mixed class coverage is manufactured. Twelve separately sampled nonretrieved diagnostic controls carry no labels.
- Completion criteria for this acquisition increment: source/text hashes and references pass; connected reserved groups excluded from all development evidence/context/suggestions; immutable CSV validation and save/reopen/import/export checks pass; manifests, holds, diagnostics, exact resume command and private cache backup delivered. The 1,000-pair goal is an unmet stretch target, not grounds to lower admission.
- Next annotation completion criterion: returned, provenance-preserving consolidated reviews and explicit adjudication of scope/quality exceptions; source holds remain binding. Training completion requires additional resolved, explicitly authorized, source-cleared genuine classes across disjoint event/copy groups; current 38 examples and models are unchanged. Evaluation still requires untouched human-labeled events, real independent judgments and adjudication/calibration; new reserved records are not gold. Public scoring remains blocked by those gates and the prior baselines' zero held-out support recall.

## Focal acquisition and component evidence — 25 October 2026

Completed the bounded acquisition/recovery increment: 923 attempted URLs, 579 stored documents, 48 strict review candidates and 171 separate source-cleared experimental component tasks. Actual new evidence is 85 pairs, not 579 gold examples; the 200/60 goal remains unmet. Prior 561/113 packets, approvals, W1, evaluation reservations and published design/scores remain preserved.

Completion checks: 129 Python tests, protected IDs/source offsets/original-response reconstruction, idempotent no-download rerun, both practical review modes and frozen manifests. Cached originals and a private incremental source checkpoint support continuation; current productive queue is exhausted, two failed archive requests remain deferred.

Next single milestone: one consolidated return and component-protocol adjudication. Annotation completion requires reviewed, attributable, source-cleared component/strict judgments with preserved assistance/checking history; component review cannot silently migrate strict labels. Training completion requires explicit approval, resolved full targets or an approved new component experiment, genuine class coverage across disjoint event/copy groups and frozen hashes. New AI suggestions are excluded; the 38-example/eight-event baseline freeze is unchanged. Evaluation still requires untouched human judgments, independence/adjudication and calibration; no public alignment migration follows from this acquisition.
