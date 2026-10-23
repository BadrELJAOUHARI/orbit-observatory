# Dataset readiness and expanded review

Updated 23 October 2026. Public website, approved codebook, W1 and editorial public scores are unchanged.

## Reviewed return

The uploaded ORBIT_Development_Review_Badr_A_Checked.csv passed the existing return validator: all 68 IDs unique and present, every read-only evidence/context/proposition/history field unchanged. Appended 68 schema-1.2.0 annotations and separate quality responses under `.local/workflow-returns/Badr_A-development-0001/`. Annotator Badr_A and the original notes are retained. Preparation is AI-assisted; additional checks are reported but not mapped to particular records or confirmed free of prior suggestions. All 68 independence flags remain false.

Fatal import conflicts: none. One prior-label difference: R-0b635fe0a55f / B05-R1 withdrawal was support with a W1 hold; the checked return says unresolved. Both judgments and the existing scope hold remain. No earlier label or source-quality decision was silently overwritten. `validation_audit.json` reports conflicts together. Reimporting the identical submission is idempotent.

The returned labels are 4 support, 58 no stance and 6 unresolved, with no opposition/mixed examples. Across current candidate families including preserved prior reviews, there are 76 reviewed assisted judgments: 6 support, 63 no stance and 7 unresolved, across eight events. The 89 historical annotation records remain append-only; alias/transfer links do not create independent votes. Approved training labels and independently human-labeled events are both zero under the existing training policy.

## Collection and coverage

43 additional distinct focal-actor communication events: USA 8, EU 9, TUR 6, IND 7, ZAF 13. Three auxiliary events (RUS 1, UKR 2) are marked training-only and do not become displayed actors. With the ten pilot events, the inventory contains 60 document records (56 canonical documents plus four wrong-date copies) and 56 distinct communication events, spanning 2012-2026. “Distinct event” does not mean an independent human judgment or statistically independent political observation.

39 focal events are supplementary UN broad speeches; four targeted DIRCO events address Ukraine directly. The auxiliary sources are supplementary. Keep these acquisition streams explicit. Targeted searches oversample positions and cannot estimate country-period policy prevalence. Most UN events fall in September; this is not balanced quarterly coverage and cannot support annual public scores.

Versioned official-source manifests are under `source_manifest/expansion-v1/` and `source_manifest/targeted-v1/`, `targeted-v2/`. Search formulations cover support, opposition and conditions for every actor/lens. These are retrieval terms, not labels. Executed searches prioritized South Africa's coverage gap through the official DIRCO search API; other actor-domain query families are planned, not claimed executed. DIRCO returned 10 Ukraine hits, 10 Russia-sanctions hits, 9 Ukraine-military-assistance hits, and zero hits for the combined withdrawal/annexation query. Search results include false positives. One additional public lecture was rejected by the collection topic check; it is not counted as a collected event.

Four 2018 archive attachments actually contain 2017 speeches. They are retained as wrong-date mirrors, excluded from new-event counts and candidate generation. A discovered mirror inherits the evaluation reservation of any copy in its actual cluster. Original collection attempts and provisional reports remain historical, superseded by `data/expansion-v6/readiness.json` and the private cleared catalog.

Unsuccessful access includes archive 2019/2020 URLs returning 404, missing full-statement attachments, an unavailable Russian OCR language model for the 2024 source, and other recorded source failures. Consilium's prior robots restriction remains respected. No AI-generated UN transcript or UN editorial summary was collected as evidence. One 2024 Turkish attachment is a presidency press report with attributed quotations, rather than a full transcript; it is explicitly held and qualified.

The exact actor × lens × year table is `.local/expansion-v6/coverage.csv` (also JSON). It separates inventory documents/events, documents/events with candidates, passages, passage-lens pairs, reviewed relevant claims, unresolved labels, source/evidence holds and independently labeled events. Candidate retrieval is not proof of relevance or a stance. All five focal actors and lenses remain in scope; missing cells are explicit. Withdrawal evidence is particularly sparse for focal actors; India has no new policy-specific pairs after screening; Türkiye and clean EU evidence remain undercovered. The existing pilot still retains every actor/lens cell for review. There are no approved opposition or mixed labels. Russian legal-recognition and responsibility passages are contrast leads requiring Russian-language review, not manufactured negative examples.

## Source quality and review packet

The canonical expansion is private `.local/expansion-v6/`. URLs, issuer, landing metadata, delivery/publication dates, retrieval time, raw/text hashes, language, translation qualifications, event roles and extraction history are retained. Original PDFs/text and pilot offsets stay unchanged. Nine unreadable font/image extractions were recovered with pdftoppm/Tesseract into separately hashed text versions; original unusable extraction is retained. OCR still requires visual source comparison. French and Russian originals remain original-language evidence; no machine translation was created. A summit source dates its statement 15-16 June only: an exact-day hold remains, so its placeholder date cannot be treated as verified daily evidence.

51 accepted expansion passage-lens candidates passed conflict and policy screening; 41 broad/off-topic pairs are retained separately in `retrieval_diagnostics.json`. Six reserved evaluation pairs remain entirely outside development exports. Source eligibility, speaker attribution, translation, extraction quality and territorial scope are separate gates. The expanded packet contains 113 development records: all 68 returned records as read-only prior history plus 45 new tasks. Of these, 12 are new mechanically clean tasks; 78 total records remain quarantined. “Mechanically clean” is not approval for scoring or training.

One consolidated resumable interface: `.local/development-review-expanded-v2-20261023/orbit-development-review.html`, with its CSV, protected JSON baseline and manifest. Existing AI suggestions are preserved with their original provenance. **No new AI stance suggestions were generated in this expansion**, for development or evaluation events. New response fields are empty. Previous labels, notes, assistance and history are visible separately. The interface retains autosave, saved status, filters and response import/export. Export the whole CSV and return it; the validator recognizes this packet. Do not edit evidence, IDs or read-only provenance. Use source filters to defer quarantined items rather than guessing labels.

## Baseline requirements and commands

From the application directory:

```bash
PYTHONPATH=python python -m orbit_data.expansion_collect
PYTHONPATH=python python -m orbit_data.policy_search
PYTHONPATH=python python -m orbit_data.targeted_collect
PYTHONPATH=python python -m orbit_data.expansion
PYTHONPATH=python python -m orbit_data.corpus_readiness
PYTHONPATH=python python -m orbit_data.training
PYTHONPATH=python python -m orbit_data.baseline_experiment --fixtures
PYTHONPATH=python python -m orbit_data.review_import returned.csv --review-id Badr_A-expanded-0002
```

The policy-search command writes discovery outcomes under expansion-v4; targeted collection writes cached source records under expansion-v5; expansion preparation promotes a validated snapshot to expansion-v6. Intermediate artifacts remain history. The collection commands reuse hash-checked downloads; repeated builds must reproduce frozen artifacts. They never overwrite prior returns. All source full text remains in private local caches. This workspace retained earlier-session files and hash checks pass; a fresh cloud environment or fresh Git clone is not guaranteed to retain `.local/`. Preserve a permitted private backup or retrieve reproducibly from manifests and require hash equality. New raw source caches have not been published; rights clearance for public redistribution remains unresolved. Tooling and review exports are portable, but reproducible retrieval cannot recover a changed/deleted source with identical bytes without a retained private snapshot.

The baseline is TF-IDF word/phrase features plus logistic regression: it learns associations between a proposition/passage and reviewed classes. A fixture check fitted 15 artificial training events and predicted five separate artificial test events across all five labels. This verifies software wiring, not political accuracy. No real-corpus model, checkpoint, calibrated probability or new public score was produced.

The guarded real-data command is `PYTHONPATH=python python -m orbit_data.baseline_experiment --approved-dataset approved.json --run-approved --output ../.local/baseline-run-0001`. No such approved dataset exists yet; the command must refuse empty/unapproved input.

Real baseline fitting requires the existing explicit approval gates: origin=human, independent/adjudicated review status, training_approved=true, source/text clearance, no unresolved holds, and genuine classes. Require nonempty event-disjoint training and development-validation groups, at least two genuine training classes and no evaluation event/copy in training or tuning. All approved class counts currently equal zero. An assisted review does not automatically become an independently approved label. Future use of reviewed assisted labels for training would need a separately agreed policy and approval records while preserving non-independence.

Final evaluation needs untouched event/time groups, two genuine independent human judgments per item, agreement/adjudication and no AI suggestions. Prior assisted exposure disqualifies a claim of blind independent evaluation for that annotator/event. Probability calibration and later aggregate validation require separate events; training success alone is not publication approval. The transformer additionally requires a pinned model revision and compute/dependency checks.

| Decision / blocker | Current handling | Needed next |
|---|---|---|
| Territorial target bundles direction, scope and annexation | Strict target retained; partial evidence held | Review TERRITORIAL_LENS_PROPOSAL.md before any schema/codebook change |
| W1 withdrawal | Comprehensive scope remains required | No change proposed; B05-R1 remains held |
| Assisted labels and training approval | All remain assisted/non-independent and unapproved | Approve a documented adjudication/training-use policy or obtain independent approved labels |
| OCR, languages, EU common position, exact summit day | Separate source/evidence holds retained | Documentary verification and qualified language/source review |
| Class and event coverage | No approved opposition/mixed examples; sparse withdrawal and uneven periods | Targeted official acquisition plus consolidated review, without invented balance |

Next milestone: resolve the territorial component decision, adjudicate the consolidated development corpus and source holds, then freeze approved event-disjoint training/validation/calibration data. Run the guarded baseline only when its data gates pass; maintain a separate untouched final evaluation sample.
