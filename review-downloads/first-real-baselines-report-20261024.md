# First real experimental baselines

24 October 2026. This checkpoint supersedes the 23 October readiness-only assessment. No previous labeling or import round was repeated.

## What changed

Recorded the new authorization against the exact candidate **and annotation IDs** of all 113 completed development records, including the earlier 68. The grant is `annotations/authorizations/20261024-all113.json`, with matching private frozen copy. It permits supervised experimental use of the 89 resolved labels, subject to evidence gates; the 24 unresolved labels are explicitly excluded.

Canonical annotations remain unchanged: origin=ai_assisted_reviewed, actual review notes/check provenance preserved, blind independence false. The earlier records' missing record-specific independent-check field remains unasserted; the new authorization does not turn it true or deny that checking occurred. The 45 newer judgments retain their prior explicit human-check confirmation. Training policy 3.0.0 accepts the explicit record-scoped permission without requiring a newly asserted check. It does not waive source, attribution, extraction, temporal or scope rules. W1 and the approved territorial proposition are unchanged.

## Eligibility before and after

| Stage | Eligible examples | Distinct events / leakage groups |
|---|---:|---:|
| Previous freeze | 10 | 3 |
| Extended authorization, before clearances | 29 | 6 |
| After nine documentary clearances | **38** | **8** |

The final 38 include **26 earlier-review examples and 12 newer-review examples**, with 8 support and 30 no_stance. There are no eligible oppose or mixed examples. The 75 excluded records comprise 69 with remaining source holds, five additional unresolved/scope cases, and one additional text-quality case. Reasons overlap in the detailed ledger; unresolved labels total 24 across the full reviewed corpus.

| Lens | Eligible examples | Distinct events | Classes |
|---|---:|---:|---|
| Territorial recognition | 2 | 2 | no_stance 2 |
| Withdrawal | 0 | 0 | none |
| Military assistance | 4 | 3 | support 1, no_stance 3 |
| Sanctions | 9 | 6 | support 2, no_stance 7 |
| Invasion responsibility | 23 | 5 | support 5, no_stance 18 |

“Distinct events” counts grouped communications, not independent human annotators or statistically independent political observations. Some positive passages overlap within the same EU speech; they remain in the same validation group and are not separate events.

## Nine specific holds cleared

All clearances are append-only technical source decisions. Original flags, source bytes, stored text/hashes/offsets and labels survive. Each decision records a criterion, evidence-file hashes and, for documentary quotations, reproducible text offsets. `clearances.json` contains exact candidate IDs and proof references.

| Records | Flag / criterion cleared | Documentary evidence |
|---|---|---|
| EU R-d03f71113a18, R-fc66b6fb5662, R-2a5ddac8aacc | EU common-position eligibility for these responsibility passages | The cached UN docket explicitly lists European Union / Charles Michel / President of the European Council. Adopted EUCO 18/22 paragraph 1 condemns Russia's aggression and states Russia bears full responsibility. This directly corroborates the institutional policy in these passages. |
| EU R-718d1e5f1923 | EU common-position eligibility for this sanctions passage | EUCO 18/22 paragraph 5 agrees restrictive measures and identifies sanctions on Russia. |
| India R-fc61b325f540, R-ecf0e5267dba, R-4bc7ec2d64ef | Suspected extraction spaces | Visual comparison with cached original pages 5 and 11 confirms “continues”, “responds” and “Those”, with complete sentences and unchanged meaning. Stored extraction spaces and offsets remain unchanged. |
| USA X-2634b1efa52d, X-892970c976c3 | OCR source/text quality for these sanctions spans | Visual comparison with page 5 of the cached official 2015 Obama statement confirms the entire reviewed sentences and Russia/Ukraine context. No missing qualifier or material OCR substitution appears. This does not clear other spans in that PDF. |

Official corroboration:

- [EUCO 18/22, adopted 24 February 2022](https://data.consilium.europa.eu/doc/document/ST-18-2022-INIT/en/pdf), especially paragraphs 1 and 5 and the cover's explicit adoption statement.
- [EUCO 1/22, adopted 25 March 2022](https://data.consilium.europa.eu/doc/document/ST-1-2022-INIT/en/pdf), also corroborates the institutional position and provides targeted withdrawal leads.

Both predate the reviewed EU speech. These registry documents are corroboration, not newly human-labeled training events. They were not fed to the classifier as extra examples. Clearances are specific to the four EU policy passages; they do not declare every sentence, year or officeholder comment an adopted EU position. In particular, no territorial or W1 hold was removed.

The Council public document registry permitted retrieval under its own access policy. Consilium's separate website restriction was respected; no user-agent impersonation, blocked-page proxy or access bypass was used. EUR-Lex returned a robots challenge; EEAS/UN-document endpoints were inaccessible; guessed Russian English counterpart URLs failed. Those failed attempts are retained. Russian language/translation qualifications, Turkish translation holds, French review, other EU common-position cases, unrepaired spans, wrong-speaker records, and the summit's exact-day qualification remain unresolved. They were not cleared to force training.

Remaining flag counts across the reviewed records (overlapping, not additive): EU common-position 23; translation 39; language 10; OCR 5; speaker mismatch 2; press-excerpt qualification 1; exact-day qualification 1; W1 hold 1; other scope-insufficiency flags 2. One additional raw page-header span still has a returned text-quality deferral even though its mechanical flag list is empty. These source/scope cases remain separate from classifier uncertainty and from the model's errors.

## Models that actually ran

Used the prepared fixed word TF-IDF (one- and two-word features) plus balanced logistic regression. TF-IDF represents words and short phrases numerically; logistic regression learns associations with the reviewed classes. No transformer or hyperparameter search ran.

Each feasible lens uses leave-one-connected-event-group-out validation. Every held-out group is entirely excluded from that fold's vocabulary fitting and classifier training. Existing copy/translation/overlap grouping and reserved evaluation groups are unchanged. Both represented classes must remain in every training fold. The majority comparator predicts the most frequent **training-fold** class, with deterministic tie breaking; it never uses held-out labels to choose the prediction.

| Lens | Examples / events | Validation folds | Event-weighted accuracy: classifier / majority | Macro-F1: classifier / majority |
|---|---|---:|---|---|
| Sanctions | 9 / 6 | 6 | **75% / 75%** | 0.438 / 0.438 |
| Responsibility | 23 / 5 | 5 | **50% / 60%** | 0.425 / 0.439 |

Event-weighted accuracy gives each event equal total weight regardless of its number of passages. Macro-F1 gives the two observed classes equal emphasis. Claim-level accuracy is 7/9 (77.8%) for sanctions and 17/23 (73.9%) for responsibility, illustrating why passage counts alone can look more favorable than event performance.

Neither classifier beats the majority comparator. **Held-out support recall is zero for both models**: all two sanctions support examples and all five responsibility support examples are missed. Responsibility additionally produces one false positive among no_stance examples. These are useful negative baseline results, not validated stance measurement.

Fold results (classifier / majority accuracy):

| Lens | Held-out event | Examples | Classifier / majority |
|---|---|---:|---|
| Sanctions | USA UN, September 2022 | 2 | 100% / 100% |
| Sanctions | ZAF DIRCO, April 2022 | 1 | 100% / 100% |
| Sanctions | USA UN, September 2015 | 2 | 50% / 50% |
| Sanctions | EU UN, September 2022 | 1 | 0% / 0% |
| Sanctions | India UN, September 2022 | 2 | 100% / 100% |
| Sanctions | ZAF UN, September 2023 | 1 | 100% / 100% |
| Responsibility | USA UN, September 2022 | 2 | 0% / 0% |
| Responsibility | ZAF DIRCO, April 2022 | 2 | 50% / 100% |
| Responsibility | EU UN, September 2022 | 3 | 0% / 0% |
| Responsibility | India UN, September 2022 | 6 | 100% / 100% |
| Responsibility | ZAF UN, September 2023 | 10 | 100% / 100% |

Saved **two final experimental lens pipelines plus eleven fold pipelines**, and 32 out-of-group experimental prediction records. The fitted pipelines include preprocessing/vocabulary, not just classifier coefficients. Artifacts include dataset/policy/model hashes, fixed preprocessing, runtime versions, per-fold class counts, event IDs, predictions and majority results. Reload/checksum checks passed.

Publication genres are mixed for classifier development, not pooled into country-period measurements. The per-example source-stream sidecar preserves publication/acquisition methods; UN and press-release comparison streams remain separate for aggregation.

These are tiny, purposively acquired, AI-assisted human-reviewed development samples. No blind independent evaluation occurred, no final evaluation was touched, and probabilities are uncalibrated. Support-versus-no_stance experiments do not validate opposition detection, general political alignment, country-period estimates or annual scores. All alignment_score fields stay null; no_stance is never neutrality. Existing visual design and public scores remain unchanged.

## Other lenses and targeted gap retrieval

- Territorial recognition remains blocked by a single class. It needs comprehensive-scope/non-recognition evidence with reviewed directional labels across additional events; no generic integrity inference or protocol broadening occurred.
- Withdrawal remains blocked by zero eligible reviewed examples. The retrieved Council conclusions provide explicit entire-territory wording compatible with W1, but new labels are not automatically approved. Repeated copied wording would still be grouped.
- Military assistance has both classes, but support occurs in only one event. It needs a second approved support event; otherwise the held-out support fold has no support class to learn.

Two tightly targeted registry documents were additionally retrieved for those gaps: [adopted Strategic Compass, 7371/22, 21 March 2022](https://data.consilium.europa.eu/doc/document/ST-7371-2022-INIT/en/pdf), and [EUCO 31/22, 21 October 2022](https://data.consilium.europa.eu/doc/document/ST-31-2022-INIT/en/pdf). The former explicitly discusses military equipment and the Ukrainian armed-forces assistance package; the latter explicitly rejects annexation and demands entire-territory withdrawal. They are exposed development/acquisition leads, not final evaluation material. Neither supplies an approved label for this run.

**Only one new decision is requested:** C24-M1, the Strategic Compass military-assistance paragraph, with an AI-generated support suggestion. Its exact original text, context, source, adoption evidence, page comparison, hashes and offsets are in `../.local/targeted-gaps-20261024/new_decision.json` and `ONE_NEW_DECISION.md`. Human label/annotator and training approval remain empty/unapproved. It is not part of the 113-record grant or current models. Confirm/correct the label and separately approve its experimental training use if appropriate. No general labeling batch or relabeling of completed work is requested.

## Outputs and commands

Private frozen dataset: `../.local/experimental-baseline-v2/`.

```bash
PYTHONPATH=python python -m orbit_data.authorized_dataset
PYTHONPATH=python python -m orbit_data.experimental_baseline --dataset-root ../.local/experimental-baseline-v2
PYTHONPATH=python python -m orbit_data.baseline_experiment --dataset-root ../.local/experimental-baseline-v2 --approved-dataset ../.local/experimental-baseline-v2/dataset.json --run-approved
PYTHONPATH=python python -m orbit_data.backend --dataset-root ../.local/experimental-baseline-v2 --port 8765
```

`dataset_manifest.json` hashes the 38-row dataset, 113-record inclusion/exclusion ledger, authorization, nine clearances, unchanged splits, counts, preprocessing and development-only evidence export. `experiment/experiment_report.json` hashes all model and prediction artifacts. Repeated runs verify/reuse an identical experiment; new data needs a new version. Historical reviews, authorizations and v1 files remain intact.

The read-only local API exposes 113 reviewed development evidence records, 38 training-included examples, and 32 clearly experimental fold predictions. Reviewed annotations and the new training grant remain separate; original/effective source flags and clearance IDs are inspectable. No predictions are connected to public scores. RUS/UKR stay auxiliary and never become displayed planets; all five displayed actors and policy lenses remain release scope.

Next single milestone: resolve the one new military-assistance decision and, if approved, run that third lens with the unchanged event-group protocol. The two existing models remain experimental and unsuitable for publication; their missed-support errors must guide later targeted data growth before transformer fine-tuning.

Verification: 89 focused tests pass, including legacy authorization without new check assertions, documentary hashes/quoted offsets, retained W1/defective-span gates, event-group isolation and training-fold-only majority selection. Live API and model restoration checks passed. Repeated dataset/experiment runs preserve artifact hashes.
