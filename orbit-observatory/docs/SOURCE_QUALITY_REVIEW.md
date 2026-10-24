# Pilot source-quality review, 23 October 2026

This is an assistant source/provenance review, not human stance annotation, model output or independent intercoder validation. The reproducible metadata/extraction checks and qualified lens screens are in data/pilot-v1/source_review.json. All ten artifacts were inspected using source headers and policy-context windows for metadata, attribution and extraction risks; this is not exhaustive human reading. Checks used the cached primary documents and official UN landing-page headings, not the AI transcript or a press-summary substitute. No audiovisual check of actual delivery was performed.

## Document audit

Dates below are the official stated event dates, checked against the archive page or the UN actor/speaker/date docket and the attached prepared speech where available. UN publication dates remain unknown rather than inferred from delivery dates. The US archive dates agree with the stored publication dates; Biden's page also exposes a 24 February 2022 publication timestamp.

| Document | Verified actor, issuer/role and stated date | Qualification |
| --- | --- | --- |
| us2014 | USA; White House / President Obama; 12 March 2014 | White House Office of the Press Secretary page. Joint availability also contains Prime Minister Yatsenyuk's remarks and reporter questions. Those are not US positions. |
| us2022 | USA; White House / President Biden; 24 February 2022 | Official historical archive; prepared remarks plus questions/answers. Quoted Kremlin assertions are rejected by the speaker. Aid, US combat deployment and NATO deployment must be separated. |
| eu-unga77 | European Union; Charles Michel, President of the European Council; 23 September 2022 | Official UN docket explicitly designates European Union, not a national delegation. English prepared speech. Common-position eligibility still requires passage-level corroboration. |
| eu-unga78 | European Union; Charles Michel, President of the European Council; 21 September 2023 | Same delegation/role verification. French prepared speech, with duplicate page numbers. French review and common-position corroboration required. |
| tur-unga77 | Türkiye; President Recep Tayyip Erdoğan; 20 September 2022 | UN-hosted English PDF explicitly marked UNOFFICIAL TRANSLATION. Previous “official English” wording described the host, not certified translation quality; provenance has been corrected. |
| tur-unga78 | Türkiye; President Recep Tayyip Erdoğan; 19 September 2023 | English PDF marked Courtesy Translation and Check against delivery. Turkish original and translator certification were not collected. |
| ind-unga77 | India; External Affairs Minister S. Jaishankar; 24 September 2022 | Prepared text marked CHECK AGAINST DELIVERY, with running headers, broken words and PDF line wraps. Counterterrorism sanctions are not sanctions against Russia. |
| ind-unga78 | India; External Affairs Minister S. Jaishankar; 26 September 2023 | Genuine official statement, with no explicit Ukraine mention in the extracted text. Generic integrity principles do not establish an exact Ukrainian territorial position. |
| zaf-unga77 | South Africa; International Relations and Cooperation Minister Naledi Pandor; 21 September 2022 | Official UN-linked statement. Refers to war in Eastern Europe without an explicit Ukraine mention. Other conflicts and general weapons references create false retrieval hits. |
| zaf-unga78 | South Africa; President Cyril Ramaphosa; 19 September 2023 | PDF includes V7, scheduling notes and running headers. Ukraine peace initiative is discussed; sanctions concern Cuba/Zimbabwe and annexation material concerns Israel/Palestine. |

Canonical/attachment URLs, checked source headings, hashes, language, findings and per-lens screens are recorded for every document in source_review.json. All existing text hashes, 184 candidate IDs and offsets were preserved. Only the Turkish translation-provenance metadata was corrected; source_manifest version is now pilot-v1.1-source-review, and the metadata export was refreshed.

## EU institutional-scope decision

The primary UN docket lists “European Union / Charles Michel / President of the European Council” on both dates. The 2022 official summary further describes the Union in its observer capacity. This explicitly corroborates EU delegation representation; it is stronger than inferring representation from Michel's title alone. The linked speeches also address the Union's actions in its own name.

Neither normalized speech contains a literal “on behalf” or “au nom” formula. The docket does not prove every rhetorical sentence is an adopted common position. Under our strict common-position scope, both documents therefore have status representation_verified_common_position_gate_pending. They are suitable for annotation preparation, but none of their passages is cleared for release scoring. Obtain a Council/common-position mandate or a directly linked adopted position for each policy passage. Do not quietly broaden the EU actor to personal officeholder rhetoric. No unsupported declaration of full institutional eligibility was made.

## Genuine source versus lens evidence

Every source is retained. Authenticity does not mean a passage settles any lens. The assistant's screen has three states: potential material requiring human decision, no explicit target found in this screen, and temporally inapplicable. It does not assign human support/opposition/no-stance labels or certify exhaustive absence.

- US 2022 and EU 2022 contain specific policy material, alongside quotations and irrelevant hits. EU 2023 includes Russia-war, self-defence and sanctions/veto language requiring French scope review.
- Turkish Ukraine-integrity/diplomacy remarks, India's generic UN Charter material and South Africa's peace-initiative language must not become precise border-recognition or invasion-responsibility scores by assumption.
- India 2023 and South Africa 2022 remain genuine documents even where the screen found no explicit stance on any exact lens. Sanctions on terrorists or Zimbabwe are useful no-stance diagnostic cases for the Russia-sanctions target.
- Pre-24-February-2022 responsibility is inapplicable. The other lens study dates do not guarantee evidence exists in every year.

All human evidence-eligibility decisions remain unadjudicated. All document release_eligible fields are false at this preparation stage. The assistant's content screens are kept out of the annotation queue; do not consult them before independent coding. A single human's first pass is not two independent judgments.

## Extraction and language limits

The eight PDFs retain line wraps, page numbers and running headers; a source line may be only part of a claim. Some EU 2022 sentence boundaries are glued, and the India/Türkiye English extractions contain split words. US transcripts include multiple voices. Source text was deliberately not cleaned again: changing it would invalidate offsets. Context and full source files are supplied so reviewers can propose corrected boundaries without altering frozen evidence.

French text remains original French, with Unicode code-point offsets into its original stored normalized text. No machine translation was made. If a future aid is produced, keep it in a separate translation-aid record with document/text hash, original span, provider/model/version, time, method/prompt, translated text and a pending bilingual-review state. It must not overwrite original text or acquire original-source offsets. A non-French reader should defer the row rather than guess a substantive label. Turkish English-version labels are provisional until original-language/translation review.

## Reproduce this review

From /workspace/orbit-observatory/orbit-observatory:

    PYTHONPATH=python python -m orbit_data.source_review

This verifies the current primary artifacts and reproduces the explicitly identified assistant findings. It does not create human annotations. A changed source snapshot requires review before preparing another queue.
