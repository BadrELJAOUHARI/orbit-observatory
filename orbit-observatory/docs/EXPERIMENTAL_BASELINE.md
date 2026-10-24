# Human-verified assisted dataset and baseline assessment

Historical 23 October 2026 checkpoint. The subsequent authorization, source clearances and real model results are in FIRST_REAL_BASELINES.md.

23 October 2026. This supersedes the pre-approval training-readiness checkpoint in DATASET_READINESS.md. No annotation round was repeated and no new labeling packet was generated.

## Imported review and authorized policy

Imported ORBIT_Expanded_Review_Badr_A.csv and HUMAN_CHECK_AND_TRAINING_APPROVAL.json from the uploaded ZIP. Only these data inputs were used; the ZIP's suggested prompt and other instruction-like documents were not executed as instructions. All 113 packet IDs and immutable evidence, propositions, source/context and history fields matched. There were zero import conflicts. Exactly 45 new responses were appended; the previous 68 reviews and earlier revision/audit history remain unchanged.

The 45 new judgments are support 7, oppose 1, no_stance 19 and unresolved 18. Annotator Badr_A explicitly confirms human checking and experimental training approval for those exact IDs. Annotation schema 1.3.0 and training policy experimental-training-2.0.0 record:

| Field | Meaning / stored value |
|---|---|
| origin / ai_assisted | ai_assisted_reviewed / true; initial assistance is preserved |
| human_independent_check | true; Badr_A's reported checking of the 45 named judgments |
| training_approved | true; permission for experimental training, subject to evidence gates |
| blind_independent_annotation | false; no blind second judgment or independent evaluation gold is asserted |
| CSV human_independent / annotation independent_human | false, preserved legacy blind-annotation flags; these do not deny human checking |

The attached approval is saved with its hash and exact submitted bytes. Import is idempotent: repeating it leaves prior annotations, approval, ledger and timestamps unchanged. Canonical annotations remain separate from frozen training feature views and machine predictions. This approval does not extend automatically to the 68 legacy reviews, source clearance, codebook changes or publication.

## Frozen eligible dataset

Private output: `../.local/experimental-baseline-v1/`, relative to the application directory. The dataset manifest records hashes for the source submission, approval, versioned policy and every frozen dataset artifact.

Of the 45 newly approved records, 33 retain source/text/language/institutional/date holds, and two more are unresolved scope cases. Eighteen unresolved labels are excluded in total; 16 already overlap the source-held group. Thus **10 examples across three communication events remain eligible: support 3 and no_stance 7**. Eligible opposition and mixed counts are zero. The approval's one opposition label remains held; it was not silently treated as eligible.

W1 and the strict territorial target are unchanged. Partial scope, unresolved labels, attribution problems and extraction defects do not become supervised stance labels merely because training was approved. No stance is a classification outcome, never a zero/neutral alignment score. Every stored alignment_score is null.

Files:

- `dataset.json`: ten approved, source-cleared feature rows with exact source passages, hashes, offsets and retained annotation provenance.
- `inclusion_exclusion_ledger.json`: all 113 records, explicit inclusion decisions and overlapping exclusion reasons; 68 legacy reviews are outside this approval.
- `counts.json`: approval and eligible counts by lens, class, event and leakage group.
- `leakage_groups.json` / `training_split.json`: event partitions and copy/overlap links; reserved evaluation events remain excluded.
- `preprocessing.json`: fixed target-conditioned word TF-IDF (1-2 word phrases) and balanced logistic regression settings.
- `dataset_manifest.json`: frozen input/artifact hashes.
- `experiment/experiment_report.json`: per-lens feasibility, actual sample sizes, proposed validation folds, missing classes and reasons for skipping.
- `experiment/experimental_predictions.json`: empty because no real model could be trained defensibly.

Grouping uses whole communication events, documented mirrors/translations/joint links, identical document hashes, and substantial copied passages across events (at least 12 matching tokens and 80% of the shorter passage). Overlapping passages within a speech stay together through their event. Group construction uses text and provenance, never labels. Any reserved event reserves its whole connected group. No evaluation labels, suggestions or experimental predictions were generated or modified.

## What actually ran

The evidence-gated freeze, per-lens baseline feasibility and event-group fold checks ran on the real returned judgments. **No lens passed, so no real classifier was fitted, no model/checkpoint was saved and no validation metric was manufactured.** Software fixture checks are tests only and are not reported as experiment results.

| Lens | Eligible examples | Events | Actual classes | Why no model ran |
|---|---:|---:|---|---|
| Territorial recognition | 1 | 1 | no_stance 1 | One event and one class |
| Withdrawal | 0 | 0 | none | No eligible approved examples |
| Military assistance | 2 | 1 | support 1; no_stance 1 | Both examples belong to the same speech; a row split would leak that event |
| Sanctions | 3 | 2 | no_stance 3 | Only one class |
| Invasion responsibility | 4 | 2 | support 2; no_stance 2 | Support occurs only in the US event and no stance only in the South African event; either held-out event leaves one training class |

The fixed experiment validates each feasible lens by leaving one entire connected event group out in turn. Each represented class must remain in training when its validation group is withheld. No hyperparameter search or pooled cross-lens fallback is used. A future feasible run saves fold models and an experimental final model, out-of-group predictions, per-event/event-weighted validation, runtime versions, dataset hashes and model checksums. Probabilities remain uncalibrated and outside public scores.

Exact missing prerequisites: territorial recognition needs both another class and additional event coverage; withdrawal needs source-cleared approved examples from at least two classes/events; military assistance needs class coverage in another separate event; sanctions needs a genuine second class represented across events. Responsibility needs support and no_stance each in at least two distinct groups. One additional cleared event containing both classes could satisfy this minimal responsibility gate; that would still be a very small exploratory experiment, not publication validation.

A possible next technical route is documentary/language clearance for already approved responsibility examples in another event, such as the auxiliary Russian event. Existing language/source holds remain binding until that clearance is explicitly documented. Initial training with auxiliary examples would not make Russia a displayed actor.

## Commands

From `orbit-observatory/` (the application directory):

```bash
PYTHONPATH=python python -m orbit_data.review_import \
  ../.local/expanded-return-incoming/ORBIT_Expanded_Review_Badr_A.csv \
  --review-id Badr_A-expanded-0002 \
  --approval-json ../.local/expanded-return-incoming/HUMAN_CHECK_AND_TRAINING_APPROVAL.json
PYTHONPATH=python python -m orbit_data.experimental_dataset
PYTHONPATH=python python -m orbit_data.experimental_baseline
PYTHONPATH=python python -m orbit_data.training
PYTHONPATH=python python -m orbit_data.backend --port 8765
```

`experimental_baseline` runs feasible lenses and reports precise skips for the others. The equivalent existing pipeline command is `python -m orbit_data.baseline_experiment --approved-dataset ../.local/experimental-baseline-v1/dataset.json --run-approved` with `PYTHONPATH=python`. It accepts the frozen hash-checked dataset and delegates per-lens execution. Repeated assessment reuses an identical existing experiment, without silently replacing it. New data/clearance requires a new frozen dataset/experiment version.

## Backend connection, without publication

A separate read-only local API is prepared and tested at `127.0.0.1:8765`:

| Endpoint | Response |
|---|---|
| `/api/status` | 113 development evidence records; not_trained_insufficient_data; five displayed actors and separately identified auxiliary actors |
| `/api/evidence?actor=USA&lens=military_assistance` | Paginated exact passages/context, source/hash/offsets, reviewed annotation provenance, training inclusion and separate source holds |
| `/api/evidence?training_included=true&limit=100` | The ten included examples, with their human-verified assisted annotations |
| `/api/experimental-predictions` | Empty list, no_predictions, alignment_score=null |

Reserved event groups cannot enter these development evidence exports. Any future prediction must reference existing evidence and a saved experimental model, have validated experimental schema, and remain explicitly uncalibrated/unapproved for publication. It cannot masquerade as a human annotation or neutral score. CORS permits the existing local preview on port 8000; the frontend can later fetch the API without changing the visual design. No frontend connection, public prediction endpoint, deployment or dist/data score replacement was performed.

Checks: 84 focused tests passed, including record-scoped approval, preservation of assistance/blind flags, source/W1 gates, unresolved exclusion, copy/overlap leakage, per-lens fold feasibility and API separation. A live local HTTP smoke check returned the actual 113 evidence records, ten eligible rows and empty experimental predictions. Reimport/re-freeze checks preserved hashes. Existing website files and public scores are unchanged.

Next single milestone: clear the remaining source/language gates for already approved responsibility examples across an additional event group, then run the first event-group baseline. No general annotation batch is requested.
