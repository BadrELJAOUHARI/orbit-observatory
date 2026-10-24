# Version 1 data collection pilot

Run commands from the application directory, not the outer Git root:

    cd /workspace/orbit-observatory/orbit-observatory
    PYTHONPATH=python python -m orbit_data.collect --metadata-output data/pilot-v1
    PYTHONPATH=python python -m orbit_data.validate ../.local/pilot-v1
    PYTHONPATH=python python -m unittest discover -s tests -v

Python 3.12 was used. The current environment already has the exact versions in requirements-data.txt. On another machine, install with `python -m pip install -r requirements-data.txt`, preferably inside a virtual environment. The collector uses jsonschema for record checks and pypdf for official PDF statements. It does not run either legacy script or alter dist/data.json.

## Inputs and outputs

| Location, relative to application directory | Purpose |
| --- | --- |
| configs/v1/actors.json | All five actors, institution whitelist/exclusions, official hosts and study dates |
| configs/v1/lenses.json | All five propositions, positive/negative direction, boundaries, applicability and English/French candidate keywords |
| schemas/v1/records.schema.json | Strict JSON Schema 2020-12 definitions for documents, events, claims, annotations and predictions |
| source_manifest/v1/pilot.json | Ten explicit official-source targets, dates, extraction/identity checks and copy/translation links |
| ../.local/pilot-v1/cache/ | URL-keyed response metadata and failed-request diagnostics |
| ../.local/pilot-v1/raw/ | Original downloaded bytes addressed by SHA-256 hash |
| ../.local/pilot-v1/text/ | UTF-8 normalized text addressed by SHA-256 hash |
| ../.local/pilot-v1/records.json | Generated records, including exact candidate evidence offsets |
| ../.local/pilot-v1/report.json | Current coverage, source failures, versions, contract hashes and limitations |
| data/pilot-v1/collection.json | Optional versionable provenance/coverage export with document metadata and record-file hash, without full texts or candidate quotes |
| data/pilot-v1/access_audit.json | Observed source-access limitations and source substitutions for this pilot |

`--output PATH` selects a separate generated-output directory. Do not edit records.json by hand: each run rebuilds it. Human annotations should be managed separately in the next milestone. `--metadata-output` writes only when explicitly supplied.

Exit code 0 means all manifest targets were collected; 2 means at least one source failed, with details in report.json. Malformed manifests, invalid records, damaged caches or broken references fail rather than masquerade as a complete pilot. Validation of an empty output does not establish successful collection.

## Provenance and record distinctions

A schema is a checkable definition of a record's required fields and types. Each record has schema_version 1.0.0, a stable ID and an explicit record_type; unknown fields and unknown actor/lens IDs are rejected.

- Documents preserve manifest, canonical and final resolved URLs, title, issuer/publisher, event link, delivery/publication dates, date basis, retrieval time, language, raw/text hashes, normalization version, source stream, local artifact paths and copy/translation relations. Unknown publication dates stay null. UN landing-page dates/speakers were inspected; metadata is not a claim that the speech has been independently annotated.
- Communication events group copies of one act of communication. A later new statement remains a separate event even if its wording repeats. Grouping is manifest-based and flagged for review. All claims, copies and translations must stay together in later train/test partitions.
- Claims in this pilot are keyword-selected paragraph/lens candidates. They have pending attribution and no stance label, score or probability. A paragraph may contain multiple actual claims or irrelevant material; the same paragraph can be a candidate for several lenses.
- Annotations require origin `editorial` or `human`, annotator ID, codebook version, label, review state, time, rationale and optional superseded annotation. These are not predictions. Existing website editorial labels are not silently imported or upgraded.
- Predictions require origin `model`, model/training-data versions, calibrated status and calibration version when appropriate. Only stance-bearing predictions can carry p and 2*p-1; no-stance/unresolved predictions have null values. No prediction or annotation records were generated in this pilot.

Dataset validation additionally checks artifact hashes, safe paths, event/document membership, claim references, exact evidence substrings and temporal applicability. Responsibility for the full-scale invasion starts on 24 February 2022. Other lens dates begin with the 2012 study boundary, which does not assert historical evidence coverage. Configuration changes that alter meaning require a new version rather than reinterpreting old results.

## Extraction and offset policy: orbit-text-v1

1. Retain the original response bytes and hash before extraction. Decode HTML strictly as the manifest's explicit encoding, currently UTF-8. HTML entities are decoded by Python's HTMLParser. Exclude head, script, style, navigation, header/footer, noscript and template content. Require the configured content root and/or transcript boundary markers; fail when absent.
2. UN sources are official full-statement PDF attachments linked from the country/actor's landing page, in the manifest language. Validate the actor heading and unique PDF link. Never extract the UN press summary or AI-generated transcript as the government's statement. PDF page text is read in order with pypdf; no OCR, translation, dehyphenation or inferred missing text is performed.
3. Convert CRLF/CR to LF, normalize Unicode to NFC, collapse whitespace within each extracted line to a single ASCII space, trim line edges and drop empty lines. Join remaining lines with one LF. Preserve case, punctuation, accents and line-wrap hyphens. PDF lines are not guaranteed to be semantic paragraphs, so candidates require human boundary review.
4. Save the result as UTF-8 bytes, without an added trailing newline. text_sha256 hashes exactly those bytes. Offsets are zero-based Unicode code-point indices into this stored string, with an exclusive end: `text[start:end] == quote`. They are neither UTF-8 byte offsets nor JavaScript UTF-16 indices and do not refer to raw HTML/PDF positions. Any future browser integration must convert indices appropriately.

English/French keywords generate candidates, not relevance or stance decisions. A full speech without explicit Ukraine evidence remains a document, and general conflict/sanctions language may be irrelevant to a specific lens. Attribution, negation, qualifications and atomic claim boundaries await review. No annual estimates can be inferred from this sample.

## Caching, duplicates and repeatability

The collector checks robots.txt, uses an honest ORBIT-Pilot user agent and a minimum one-second interval per host (or a longer declared crawl delay), restricts HTTPS redirects to configured official hosts, and preserves TLS verification. A 404 robots file permits access; denial, failed policy retrieval or an unexpected robots response blocks it. There is no user-agent impersonation or permission bypass.

Downloads and retrieval times are reused by default. Hash checks reject cache corruption. Failed HTTP requests are cached too: use `--retry-failures` only after a relevant access/configuration change. `--refresh` explicitly fetches again, retaining old content-addressed artifacts. Changes to extraction can be retried against the cached bytes without a refresh.

Manifest copies/translations share event IDs. Exact normalized-text hashes identify copies within an event, which retain their source records but do not create extra annotation candidates. Explicit translations retain provenance and do not create independent event evidence. A later event with identical wording is not automatically merged. This pilot's ten selected documents have no detected exact duplicates; copy/translation cases are exercised with clearly synthetic test fixtures, not invented research observations.

The collector rewrites the generated record list instead of appending. Stable IDs include the document, text hash, lens and offsets. Two real cached executions produced byte-identical records and unchanged download metadata. Report generation timestamps may differ; a timestamp change is not a new observation.

## Coverage and limitations observed on 23 October 2026

| Actor | Collected / targeted | Material |
| --- | --- | --- |
| United States | 2 / 2 | Obama 2014 and Biden 2022 official archive transcripts, English |
| European Union | 2 / 2 | Charles Michel's UN statements, 2022 English and 2023 French |
| Türkiye | 2 / 2 | Erdoğan's 2022 and 2023 UN-hosted English statements, marked unofficial/courtesy translation |
| India | 2 / 2 | Jaishankar's 2022 and 2023 UN statements, English |
| South Africa | 2 / 2 | Pandor 2022 and Ramaphosa 2023 UN statements, English |

Ten documents and ten events yield 184 passage/lens candidates, not 184 validated atomic claims. No model was trained, no human labels inferred and no public scores replaced. The eight UN statements form a separate comparison stream from the US executive archive transcripts. This selection cannot support direct comparative annual scores or establish coverage of all 25 actor/lens combinations.

Initial requests were blocked by the cloud proxy. Source-domain additions were saved to the environment draft, after which required archive and UN collection requests succeeded. Review/save/publish of the environment configuration remains a separate product action. The original EU press-release URLs were not collected because Consilium robots.txt disallows this ORBIT user agent; official UN publications were selected instead. The EU 2023 source has a French attachment only, so it is stored in French rather than replaced with an unverified translation.

The Obama archive's copyright policy states government-produced materials are not copyright protected, with exceptions for third-party material. UN terms/copyright URLs were discovered, but requests through www.un.org were proxy-blocked during review. All full-text/PDF artifacts remain local research cache; redistribution rights and a complete terms review remain unresolved. The metadata export does not grant a license to underlying texts. Check access_audit.json for the observed limitations.

The ten-document pilot does not audit retrieval recall, annotation agreement, event-clustering accuracy or archive completeness. A source page's presence is not evidence of a stance. Next: review exact passages and event/scope metadata, write the five-lens codebook, and prepare independently double-coded annotations before any training.

## Annotation preparation follow-up

See [SOURCE_QUALITY_REVIEW.md](SOURCE_QUALITY_REVIEW.md) for the ten-document audit and [ANNOTATION_REVIEW.md](ANNOTATION_REVIEW.md) for the private 184-row queue, first 20+5 review batch, frozen codebooks and backup/restore procedure. The source manifest is now pilot-v1.1-source-review to correct Turkish translation provenance; all original text hashes, 184 candidate IDs and offsets are preserved. The source-quality screen is assistant analysis kept separate from human labels. EU delegation representation is corroborated by the UN docket, but common-position eligibility remains gated for passage-level corroboration. Human labels are still empty, and no model training or public-score change occurred.

The prior cache survives in this attached workspace and was revalidated. A verified private archive provides portable preservation; fresh cloud-machine restoration has not been tested. Git alone does not preserve the ignored cache. The full storage limits and reproducible allowed-source retrieval alternative are documented in ANNOTATION_REVIEW.md.

## Cached segmentation follow-up

Use `PYTHONPATH=python python -m orbit_data.resegment` from the application directory for the source-aligned v2 queue and reviewed-history transfers. This reads existing cached PDFs/text without collection, creates private outputs under the outer `.local/annotation-v2/`, and preserves v1 evidence. See [SEGMENTATION_V2.md](SEGMENTATION_V2.md) for output schemas, review instructions and limitations.
