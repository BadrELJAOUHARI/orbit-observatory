# Focal retrieval benchmark, 24 October 2026

This cloud has ordinary Python HTTP, caching, Playwright/Chromium, Poppler/pypdf and English OCR. It has **no connected web-search tool, Firecrawl MCP, Firecrawl API credential or scraping-service subscription**. Available tool metadata was checked in this execution environment. Laptop installations do not carry into this environment. No paid service was called.

The bounded benchmark reused 13 previously problematic official URLs: six India, four Türkiye and three South Africa. Raw results/receipts remain in `.local/focal-acquisition-v2/benchmark.json`. The original keyword-based `full_text_candidate` diagnostic overcounted indexes; the verified table below supersedes that diagnostic. A usable index is not a retrieved policy document.

| Official URL / identifier | Observed result and failure stage | Elapsed seconds |
|---|---|---:|
| MEA canonical response `38308` | HTTP returns 494-character loading shell. Rendering recovers the same complete response, not a new event. | 2.826 HTTP; 25.972 rendered |
| MEA detail API `41740` | 5,042 characters; Jaishankar remarks, 3 September 2026, named official speaker. | 4.150 |
| MEA detail API `38308` | 1,260 characters; official spokesperson Randhir Jaiswal, 19 September 2024; same response as canonical page above. | 4.152 |
| MEA detail API `34899` | 28,367 characters; complete multi-speaker briefing. Event 24 February 2022; publication 25 February. Reporter questions are not Indian policy. | 4.157 |
| MFA `/sitemap.xml` | HTTP 200 **Turkish maintenance page**, 281 characters. Failed discovery, not successful extraction. | 0.015, cached |
| MFA `/default.en.mfa` | Genuine official homepage/index. Not a policy document. Follow its press/minister archive links. | 1.321 |
| MFA `/sub.en.mfa?7cafe2ef-78bd-4d88-b326-3916451364f3` | Real but wrong archive: international-organizations navigation. Not the intended statements archive. | 0.652 |
| MEA listing, Ukraine page 2 | Structured dated discovery index, not full text. Returned predominantly pre-period records; dates are screened before admission. | 3.714 |
| Türkiye presidency `/en/speeches-statements/` | Robots response is not readable plain text; access-policy verification fails. Body not fetched through another service. | 3.056 |
| Gov.za `?search_api_fulltext=Ukraine` | Wrong search parameter silently ignored. HTTP 200 returned unrelated latest records. Discovery failure. | 0.016, cached |
| Indian UN mission `/IndiaatUNGA` | HTTP 503. No body or identity/stance clearance inferred. | 5.622 |
| SA presidency search | HTTP 503. No complete document retrieved. | 4.503 |
| DIRCO public posts API, Russia/50 | Published-post JSON with body fields is accessible. It needs per-post date, actor, conflict and policy checks; JSON itself is not one stance document. | 8.955 |

**Verified document retrieval:** three distinct complete official documents through simple HTTP; the browser recovers one canonical representation of one of those same three. Rendering used 21 same-origin resource receipts and recorded two resource errors; original HTML/resources and rendered DOM are cached. No new independent event is created for the rendered copy. Observed times include queueing, per-host throttling and cache reuse; this is a diagnostic comparison, not a controlled speed experiment. The benchmark store recorded 30 noncached URL requests and six cache hits; service usage/cost was zero paid calls, with infrastructure cost unobservable.

## Corrections adopted during collection

- **India:** the official page embeds a working `FrontEnd/FetchPublicationDetailData?pkid=…&languageId=1` contract. Its public anonymous global-search form leads to `/advanced-search-list`, whose JavaScript specifies JSON POST `/FrontEnd/AdvanceSearchDetails`, `searchBy=title+content`, dates and pagination. One verified query returned 814 indexed hits, rather than assuming title-only search covers briefings. The collector follows actual returned publication URLs and caches each body once. The public search request is not authentication; transient cookie/form state is not exposed or saved as credentials.
- **Türkiye:** follow `/press-information.en.mfa` and actual dated archives. Pagination requires the page's own hidden form state, advertised `Page$N`, Origin and Referer. A verified page-2 POST returned 25 different article links. Earlier guessed/nonadvertised pages and mismatched parent state were **collector discovery defects**, not evidence of blocking; 25 such failures are reclassified in `pagination_failure_audit.json`. Invalid requests are not retried. Corrected repeated failures stop only that archive.
- **South Africa:** the real government search input is `search_query`; the corrected Ukraine query returned 21 matching result links. Use the published DIRCO posts endpoint with small pages, then verify the issuing office. Provincial positions are held separately from national executive policy.
- **Commission:** its published client uses `global`, `documentTypeCodes`, lowercase `pagesize/pagenumber`, then slash-separated document references. JSON Accept resolves the observed 406 negotiation error. Only explicit EU representation / jointly issued Council–Commission presidential statements clear institutional scope; other Commission comments remain held. This source was a targeted follow-up, outside the original 13-URL benchmark.

Use cached HTTP for ordinary HTML/JSON/PDFs; browser rendering only demonstrated added value for the MEA shell. Do not count an index, maintenance page, out-of-period record or question as a recovered statement. Preserve `CHECK AGAINST DELIVERY` and publisher translation qualifications.

## Firecrawl and remaining capability gaps

A live comparison was impossible: no Firecrawl MCP/API access is connected here. Its usefulness is **unproven** for these URLs. Rendering may help ordinary JS shells, but the existing browser already recovers the tested MEA shell and the direct published endpoint is cheaper. A scraper cannot resolve wrong URLs, official-role ambiguity, compound-target scope or source restrictions. Dedicated web search would principally help discovery of additional official URLs.

For an existing authorized Firecrawl account, the supported optional adapter is:

```bash
PYTHONPATH=python python -m orbit_data.firecrawl_compare --max-calls 1
```

Inject the existing `FIRECRAWL_API_KEY` through this cloud environment's secret mechanism; never put it in a command, repository or chat. The adapter is not an MCP installation and does not create an account. It checks observable spare quota first, stops if quota/API compatibility cannot be verified, allows at most one known permitted source scrape and keeps the original rendered HTML. Its live quota/scrape compatibility has not been tested. Registering an MCP tool requires the application's connector settings; installing a Python/npm package cannot add callable MCP tools to this turn.

Representative unresolved routes: `https://pminewyork.gov.in/IndiaatUNGA` (503), `https://www.thepresidency.gov.za/search?search_api_fulltext=Ukraine` (503), `https://www.tccb.gov.tr/en/speeches-statements/` (robots verification), `https://www.pmindia.gov.in/en/news_updates/` (403). Türkiye's communications site explicitly declares `ai-input=no` and `ai-train=no`; its policy pages were not collected or sent for AI preparation. No alternative fetcher is used to bypass these restrictions.

## Unicode URL repair

The final failure-stage audit found 18 Python ASCII URL-encoding errors on Turkish archive links. These were local transport-formatting defects, not access denials. Standard percent encoding recovered ten dated original documents; old failures remain in attempt history. No host/UA/permission change or external scraper was used.
