# ORBIT annotation codebook 1.0.0

Frozen operational instructions for the first human pilot, 23 October 2026. These rules are finalized for this batch, not empirically validated. Independent coding and adjudication may justify a new version; never silently change labels already collected under this version. The five lens sheets below share these rules and configs/v1/lenses.json propositions. This is not a training run.

## The task

Read the exact passage, surrounding context, source metadata and the stated policy proposition. Decide what the specified actor itself asserts about that proposition at the event date. Topic words, sympathy, peace advocacy, economic hardship and generic legal principles are not automatically policy stances. The unit supplied here is a candidate passage/lens pair, often a PDF line rather than an atomic claim. Do not label the entire country, speech or year.

Use only the passage as evidence, with context to resolve references, negation and speaker. If decisive evidence is only in surrounding context, note its exact words and location as a proposed new/expanded span. Do not silently extend the supplied evidence. Leave IDs, text, offsets and hashes unchanged. Request a split when a passage contains distinct attributable policy claims. Future scoring must use reviewed atomic spans, not these raw paragraph candidates.

## Labels

| Label | Meaning and boundary |
| --- | --- |
| support | The actor asserts/endorses the lens proposition within the required target and scope. Record qualifications; do not generalize a restricted policy to a broader one. |
| oppose | The actor explicitly rejects that proposition or endorses its defined opposite. Silence, hedging, peace talks and refusal to take sides are not opposition. |
| no_stance | The passage is interpretable but gives no attributable stance on this exact target: another country, another policy, a reporter's question, an unendorsed quotation, or insufficient specificity. Record the reason. This is not neutrality or a numeric zero. |
| mixed | Both support and opposition remain in an attributable passage and cannot yet be separated into coherent atomic spans. Explain each component and request a split/adjudication. Different positions on different lenses are not mixed within either lens. Never average mixed into zero. |
| unresolved | A substantive attribution, reference, meaning or scope ambiguity prevents a defensible decision even with context. State the ambiguity. Do not use this for a clear absence of the target. |
| not_applicable | Administrative exclusion: event date is outside the proposition's applicability period. It is distinct from the five substantive labels and receives no score. |

All of no_stance, mixed, unresolved and not_applicable remain outside binary stance scoring until reviewed under an explicit eligibility policy. Human support/oppose labels also do not become model probabilities. No score is calculated in this milestone.

## Rules that apply to every lens

1. **Attribution first.** The document's issuer is not necessarily the speaker of every sentence. In the 2014 US transcript, Yatsenyuk is a Ukrainian speaker, not the US government. Reporter questions in either US transcript are not presidential positions. Clearly foreign/reporter speech without endorsement is no_stance for the designated actor; uncertain speaker boundaries are unresolved. Record the actual speaker in notes.
2. **Quotations.** A quoted third-party position belongs to that third party unless the target actor explicitly endorses it. Preserve reporting verbs and the rejection/endorsement around the quote. Sarcasm, rhetorical questions and a quoted claim introduced as a lie cannot be labeled by the quote alone. If the decisive rejection is outside the exact span, request expansion.
3. **Negation.** Resolve what is negated and by whom. “We do not oppose assistance” and “we do not provide assistance” mean different things; the latter does not necessarily oppose other countries supplying it. Do not infer double-negation entailments when the intended commitment is unclear.
4. **Conditionals and time.** Separate an endorsed conditional policy (“we support X if C”) from a hypothetical, warning, counterfactual or quotation. Record C, the time referred to and any policy restriction. A condition that leaves the exact proposition undecided requires no_stance or unresolved, not assumed unconditional support. Historical reporting alone is not a current endorsement. A current reiteration of a prior stance can be coded, with its stated time retained.
5. **Partial scope.** Record territory, aid type, measure, recipient, conditions and exceptions. If the passage only settles a narrower/different target than the fixed full proposition, do not promote it to a complete position. Use no_stance for a clear narrower claim that does not decide this target, or unresolved if the referent/scope itself is ambiguous. Preserve the narrower claim in notes for a future explicitly versioned sub-proposition.
6. **Mixed claims.** First try to split conflicting or differently scoped claims. Neither opposing direct troop deployment while supporting weapons deliveries nor supporting Ukraine on one lens while opposing sanctions on another makes both lenses mixed. Apply the appropriate proposition separately.
7. **Eligibility and EU scope.** An authentic official document can contain no eligible evidence for a lens. The UN identifies Michel as the EU's European Council President, corroborating delegation representation; that alone does not prove every sentence is an adopted common position. Both EU sources remain gated for confirmation of the relevant passage's common-EU mandate. Do not treat member-state, Commission-only or personal positions as EU common positions. Record scope concerns in notes; do not infer a release-eligible score from this exercise.
8. **Language and translations.** Preserve original text and offsets. French requires a reader able to assess the original. If you cannot, leave label blank, set review_status to needs_language_review and identify the issue in notes. This is a workflow limitation, not a substantive unresolved stance. The Turkish English attachments are marked unofficial/courtesy translation and require original-language corroboration before final evidence use. No machine translation is supplied. Any later translation aid must be separate, with source hash, provider/model/version, date, prompt/method and reviewer status; it cannot replace original evidence.
9. **Dates.** Territorial recognition, withdrawal, assistance and sanctions use the study window starting 1 January 2012, with no promise of coverage. Responsibility for the full-scale invasion applies from 24 February 2022 onward. Later discussion of 2014 is not automatically a position on responsibility for the 2022 invasion. All end dates are open unless a future version changes them.
10. **No fake independence.** One person's two passes are not two independent annotators. Use separate copies and distinct IDs for two actual humans, without seeing each other's labels or machine suggestions. Preserve both judgments before adjudication. The source-quality review is assistant analysis, not a human label or an independent annotation.

## How to return the first batch

Open first_batch.csv in a spreadsheet using UTF-8, comma separation and quoted multiline cells, or edit first_batch.jsonl with a suitable editor. Copy it to a new filename for your annotator ID. Fill only label, annotator_id, review_status and review_notes. Use review_status annotated for a decided label, needs_adjudication for a substantive problem, or needs_language_review with an empty label. For mixed/unresolved, explain the problem; for narrower scope, identify it. An arbitrary stable identifier such as Badr_A is enough; no personal details are required.

Do not edit or translate exact text, IDs, URLs, offsets, provenance or grouping. The same passage can appear for multiple lenses; label each proposition separately while keeping its shared passage_id/event_id. For random retrieval controls, judge the assigned proposition and note any other omitted policy claim in review_notes. Do not create an event for a control.

Save the file as UTF-8 CSV or JSONL, retaining all rows and columns, and attach the returned copy to the chat. Partial returns are useful; leave undecided labels empty and explain blockers. These 25 rows are a diagnostic/codebook batch, not representative evaluation data. Human labels will be validated before any later import or training.

Lens sheets: [territorial recognition](territorial_recognition.md), [withdrawal](troop_withdrawal.md), [assistance](military_assistance.md), [sanctions](sanctions.md), [responsibility](invasion_responsibility.md).
