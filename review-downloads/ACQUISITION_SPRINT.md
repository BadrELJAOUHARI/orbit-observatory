# Targeted acquisition checkpoint — 24 October 2026

561 new clean development passage–proposition pairs, 521 distinct passages, 255 source documents and 255 communication-event records. Conservative copy/day/overlap grouping leaves 238 development leakage groups. These are source/event units, not independent human annotations.

Focal actors contribute 189 pairs / 70 events / 62 groups. Auxiliary UK contributes 372 / 185 / 176; it is not a displayed planet. The 1,000-pair stretch goal is **not met**. The combined event goal is met only when auxiliary material is counted; focal coverage remains incomplete.

| Actor | Clean pairs | Events | Leakage groups |
|---|---:|---:|---:|
| USA | 141 | 55 | 47 |
| EU | 47 | 14 | 14 |
| TUR | 0 | 0 | 0 |
| IND | 0 | 0 | 0 |
| ZAF | 1 | 1 | 1 |
| GBR | 372 | 185 | 176 |

Years: 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026. All new clean exports are English official publications. Older French/Russian evidence and its qualifications remain unchanged. Lens counts: {'sanctions': 142, 'invasion_responsibility': 337, 'military_assistance': 65, 'troop_withdrawal': 13, 'territorial_recognition': 4}. The full actor × lens × year table is coverage.csv; zero cells remain explicit.

## Acquisition and admission

1398 candidate source URLs processed in 54 resumable batches; 40 saved discovery queries, plus original probes and reused prior search results. 858 usable document extractions stored; 855 are newly acquired source URLs rather than prior clearance copies. This download inventory is **not** the clean sample. 691 development pairs remain held; 51 passage diagnostics and 15 duplicate links are separate. Document-level inaccessible/irrelevant/non-adopted outcomes are in source_failures.json, not silently discarded.

694 new reserved passage–lens records are excluded entirely from review HTML/CSV/backup and suggestions; that count includes held material and is not evaluation gold. Existing reserved evaluation passages were not opened. Previously known source URLs/hashes and event metadata were reused for copy protection. New splits precede suggestions, and reserved status wins across same-day institutional releases, whole-document copies and exact 80-word overlapping text. Grouping is conservative and can remove many otherwise useful development examples. Mirrors and overlapping passages are not independent samples.

Clean admission requires conflict/policy relevance, attributable official institutional text, source date/language, complete boundaries and exact stored offsets. Weapons supplied to Russia, humanitarian-only aid, unrelated sanctions and navigation-only passages are excluded. Joint signatories/third-party quotations, defective extraction and strict target insufficiency remain separate holds. Partial Crimea/territorial-integrity evidence does not satisfy the strict compound target. W1 is unchanged: unqualified withdrawal does not silently become comprehensive legal-territory coverage.

## Suggestions, controls and review

Proposed classes: {'support': 457, 'unresolved': 104}; approved new labels: **0**. The actual method is assistant-authored deterministic literal-cue rules (sprint-admission-suggestions-1.0.0), with an unresolved fallback for conditions/unclear polarity. No per-record LLM inference, model probability, independent human judgment or Badr_A checking is claimed. Rules are fallible proposals; source action versus policy endorsement and invasion initiation versus incident attribution need review. No opposition/mixed coverage is invented. This corpus is deliberately selected for training acquisition and must not be used as an annual position estimator.

Open orbit-development-review.html locally. Filter actor, lens, year and proposed label; unresolved suggestions come first. Enter your annotator ID, a label and brief reasoning. The browser autosaves; keep a progress JSON backup. Export the entire return CSV, even for a partial review; untouched human fields remain blank. The source fields and old provenance must remain unchanged. Return validator command:

```bash
PYTHONPATH=python python -m orbit_data.review_import returned.csv --review-id Badr_A-sprint-0003
```

The packet contains only new clean tasks; the 113 completed reviews are not repeated. Twelve deterministic hash-sampled nonretrieved passages are saved separately in retrieval-controls.json, with no suggestions/labels. Held material is in relevant-held.csv / held.json, not added to your clean review workload. Existing C24-M1 and the territorial-component proposal remain pending; neither blocked this sprint and no codebook change was applied.

## Bottleneck and next acquisition

Source nonadmission stages: {'conflict_relevance': 127, 'url_discovery_wrong_or_unavailable_docket': 164, 'page_access': 8, 'source_clearance': 224, 'text_extraction_or_source_format': 17}. URL discovery was improved using Treasury's official year shards, filtered GOV.UK APIs, DIRCO's official post API and the independently permitted Council registry. Smaller DIRCO pages recovered queries after larger requests timed out. Earlier-period Council docket searches had poor marginal yield; repeated failures are cached rather than retried indefinitely.

For targeted India/Türkiye coverage, **page access and reliable URL discovery** are the main remaining obstacles. A final supplementary UN gap search tried 30 additional source URLs and retained five genuine 2026 delegation documents, including India and Türkiye; these supplied no new clean exact-target pairs. Türkiye/Ukraine translation and EU institutional-scope holds remain. Some other UN PDFs have unusable embedded font maps; the failed extraction and cached original are retained for source-preserving OCR/language review, rather than misreported as political irrelevance. For sources already downloaded, strict relevance/scope/attribution filtering and split protection are the largest attrition stages. Native PDF extraction works for the clean sample but defective spans stay held. Per-stage counts are not timings; no latency estimates were fabricated. Twelve additional MEA search failures are preserved in auxiliary_query_receipts.json as side-route attempts, separate from the 40 main discovery queries.

Firecrawl MCP is not available here. It may improve discovery and permitted JavaScript rendering; it cannot remove robots/access restrictions or guarantee 403 recovery. Needed capability: a reachable, permitted rendered-page fetcher with a trusted certificate chain and an official-source search API. Representative failures: MEA detail endpoint `https://www.mea.gov.in/FrontEnd/FetchPublicationDetailData?pkid=41740&languageId=1` (tunnel/403/shell access), `https://www.mfa.gov.tr/sitemap.xml` (maintenance body), `https://www.defense.gov/News/Releases/Tag/46928/ukraine/` and White House WP endpoint (403). The MEA Chromium probe recorded a certificate-chain error; it did not bypass validation. No tools were installed and productive retrieval continued.

## Resume and persistence

From the app directory, exact idempotent resume command:

```bash
PYTHONPATH=python python -m orbit_data.acquisition_sprint --resume --discover-gaps --discover-earlier-council --discover-un-gaps --batches 50 --batch-size 30 --finalize
```

state.json retains processed queries, errors, pending/in-flight tasks, source receipts and batch counters. URLs already processed are skipped, including cached failures; this command may do no new network work when all currently discovered leads are exhausted. A new permitted discovery route or reviewed new manifest is then required. Interrupted in-flight tasks are recovered; successful downloads are hash-checked before reuse. Five workers, per-host locking and 1.1-second minimum request spacing bound retrieval. No restriction evasion is used.

Original HTML/JSON/PDF bytes are in `.local/acquisition-sprint-v1/raw/`, extracted text in `text/`, and hashed URL receipts in `cache/`. Stored text is NFC, line-horizontal whitespace normalized; physical PDF line breaks remain. Exact spans/context use Unicode code-point half-open offsets into this unchanged stored text. Display reflow is only a reading aid. Source/event manifests and schemas/acquisition-v1 retain institutional, date, language, selection and grouping provenance.

The current workspace retains these files across its sessions; a fresh environment is not guaranteed to retain them. Preserve the private source checkpoint alongside the review ZIP. Restore its `.local/` tree under the repository root (parent of the app directory). Keep private cached source bytes private where redistribution is unresolved; canonical URLs, receipts and commands support permitted reproducible retrieval. The development ZIP contains **no reserved evaluation text**; the separate technical source checkpoint contains cached sources and must never be used as a development export.

The existing **38 approved eligible examples / eight events**, all 113 review histories/authorizations, earlier scope/source holds, model files, website and public scores remain unchanged. No new suggestion is training-authorized; no unchanged baseline was rerun. Next milestone: review the consolidated clean packet while opening a permitted official-source route for India/Türkiye and explicit contrast evidence. Training may resume only after additional eligible labels are approved.
