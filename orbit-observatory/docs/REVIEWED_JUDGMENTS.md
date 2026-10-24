# Reviewed assisted judgments and span history

Review review-0001 records Badr_A's user-supplied decisions for B01–B05. Provenance is exactly: “AI-assisted judgments reviewed by Badr. These are not independent human annotations.” They are not independent gold labels, model predictions or adjudications between independent humans. No model call supplied additional labels in this milestone.

## Stored artifacts

- annotations/v1/reviews/Badr_A/submission-0001.json preserves the submitted labels and reasoning.
- annotations/v1/reviews/Badr_A/review-0001.review.json maps batch IDs to the existing candidate IDs and stores five canonical annotation records. Reasoning is retained in review_notes and the legacy rationale field. B01 is excluded for actor mismatch; original B05 is excluded for a defective span. No record is scored.
- annotations/v1/reviews/Badr_A/review-0001.attribution_audit.json adds a marker-based speaker audit without modifying the preceding source-quality audit.
- The private outer .local/annotation-v1/reviews/Badr_A/review-0001/ directory contains reviewed_first_batch.csv/jsonl, overlay_records.json, B05-R1.claim.json, B05-R1.task.json, and the still-blank B06-B10.csv/jsonl. CSV is a convenient task view; the canonical review ledger carries the accurate assisted/non-independent provenance.

The original blank 25-row batch, 184-row queue, cached source records/text, prior audits and prior portable archive are unchanged. That earlier archive predates this review. New decisions live in an append-only ledger; correction requires a new review ID and a supersedes link, not replacement of the original reasoning. Repeating the identical recording command verifies/reuses its existing ledger rather than duplicating annotations. A changed submission cannot overwrite it.

## Necessary schema additions

The old annotation schema 1.1.0 allowed only human/editorial origins and unreviewed/independent/adjudicated states. None accurately described an AI-assisted decision reviewed by Badr without independent annotation. New schemas/v1.2/annotation.schema.json specializes this workflow with origin ai_assisted_reviewed, review_status reviewed_non_independent, required review_provenance, ai_assisted=true, independent_human=false, batch_id, review_notes and an explicit scoring_status. It rejects labeling this workflow independent. Versions 1.0.0 and 1.1.0 remain intact. No probabilities or scores were introduced.

New schemas/v1.1/claim.schema.json permits a traceable review_requested_span_expansion_v1 with revision_of, reason, requester and creation time. The old claim's keyword-selection method would misdescribe a requested manual span repair. New schemas/annotation-v1.1/task.schema.json identifies its linked follow-up task. Both retain the same document, event, lens and original text hash; validation checks that the new span contains the old one and reproduces the exact stored text.

## B05 revision

Original candidate claim-185ca2786434dc8d182aa8285e0110bf207612ccecdcc81a82e8423ff21261be remains at [4236, 4324), with Badr's unresolved judgment and defective-span explanation.

New candidate claim-revision-23300a15e6dd281d3917fffa0e6bf107a6ff83e3d4bdfa511e84d8b6614ff316 is task B05-R1, at [4209, 4382), in doc-eu-unga77 / event-eu-unga77. It contains the complete sentence, retaining the source's LF line breaks. Original raw/normalized text is unchanged. Its label, annotator, review status and review notes remain empty for a new decision. Do not transfer the parent's unresolved label, assume support, add “all internationally recognized” to the source, or infer institutional eligibility. Exact territorial scope and the existing EU common-position gate still need review.

## Attribution audit

Screened all 69 candidate/lens pairs across both relevant US transcripts. Sixteen were flagged: two in Yatsenyuk's speaker block in doc-us2014, including reviewed B01, and fourteen reporter-question pairs in doc-us2022. The fourteen pairs include some passages retrieved for more than one lens; they are not fourteen separate events. The other 53 pairs merely have no marker mismatch detected, not certified attribution. The screen cannot resolve unmarked changes or third-party quotations inside a presidential turn.

Each flag retains the candidate/document/event IDs, offsets and overlapping speaker-marker segments. It places unresolved attribution behind a review gate without assigning stance labels. Only the five user-supplied judgments are annotated. B02/B03 keep their shared passage and event links; assistance and direct combat participation remain distinct in the stored reasoning.

## Commands

From /workspace/orbit-observatory/orbit-observatory:

    PYTHONPATH=python python -m orbit_data.reviewed
    PYTHONPATH=python python -m unittest discover -s tests -v

Recording validates the five canonical annotations and new span against the 204 original source records, producing a 210-record validation view without overwriting the original corpus. It also validates the returned task copy against the original batch. Twenty original task labels remain blank. B05-R1 and B06–B10 are ready for the next user review; they do not yet have labels.
