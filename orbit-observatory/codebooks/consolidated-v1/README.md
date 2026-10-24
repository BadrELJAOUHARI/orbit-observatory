# Consolidated annotation protocol 1

This is the single working reference for bulk review. It consolidates frozen codebooks/v1.0.0, the strict v1.0.1 clarification and Badr_A's explicit W1 decision in v1.0.2. It does not broaden any target or revise a submitted judgment. Configurations remain configs/v1/. AI suggestions are a separate, unreviewed record type, not human annotations or trained-model predictions.

## Exact targets and lens-specific boundaries

| Lens | Target proposition | Binding boundaries |
| --- | --- | --- |
| Territorial recognition | Ukraine has sovereignty over all its internationally recognized territory; annexation has no legal recognition. | Both comprehensive territory and legal non-recognition must be established. Generic sovereignty is insufficient. Ukraine-specific integrity alone is partial evidence, not automatic complete support. Legal recognition differs from de facto control. |
| Russian withdrawal | Russian forces should withdraw from all internationally recognized Ukrainian territory. | W1 is settled: comprehensive scope is required. Explicit equivalent wording can establish it without magic words; absence of a territorial exception alone cannot. Unqualified withdrawal from Ukrainian territory remains scope-held. Ceasefire and negotiations alone establish neither direction. |
| Military assistance | Supports external military assistance to Ukraine, with type, recipient and conditions preserved. | Distinguish humanitarian aid, Ukraine's own self-defence, Russian military activity and NATO territorial defence. Providing aid and ruling out direct US combat are compatible. Preserve aid type, beneficiary, deployment/use restrictions and conditions. |
| Sanctions | Supports specified restrictive measures against Russia because of its actions in Ukraine. | Retain measure, target and exceptions. Opposition to sanctions on Zimbabwe or terrorism sanctions is not opposition to Russia sanctions. Claims about effectiveness alone do not automatically endorse or oppose a measure. |
| Invasion responsibility | Attributes responsibility for the February 2022 full-scale invasion to the Russian state. | Applies from 24 February 2022. Explicit attribution to Putin/the Kremlin as state leadership can establish responsibility. References to conflict, its consequences, peace or responsibility for other duties do not. |

## Labels

| Label | Rule |
| --- | --- |
| support | Attributable endorsement of the exact qualified target, including explicit equivalent wording. Do not promote partial scope to full support. |
| oppose | Explicit rejection of that target or endorsement of its defined opposite. Silence, neutrality claims, negotiations or criticism of another actor are insufficient. |
| no_stance | No attributable position on the specific target in this passage. Unrelated countries/conflicts and humanitarian or NATO references can be genuine source text with no relevant stance. It is not a neutral directional score and does not mean the actor has no policy. |
| mixed | Both support and opposition to the same target under comparable qualifications remain after attempting a defensible split. Positions on different targets or aid versus direct combat are not mixed. |
| unresolved | Relevant evidence cannot yet be assigned a final direction. Record the reason separately: partial scope, ambiguous endorsement, unresolved attribution or defective evidence. Never treat these distinct reasons as one model-uncertainty estimate. |
| not_applicable | Administrative date exclusion, distinct from the five substantive labels. |

## Context, attribution and language

1. Check the actual speaker. A White House transcript can include Ukrainian officials and reporters. Foreign speech and questions do not establish US stance. Preserve the original B01 no_stance plus its attribution exclusion. Quarantine other unresolved attribution cases; do not automatically label them.
2. Resolve quoted speech, reported allegations, negation and pronoun antecedents. A quotation is not endorsement. Rejection of a fabricated threat can support invasion attribution without establishing a military-assistance position. Context resolves referents and qualifications; it must not donate an unrelated neighboring claim to the central span.
3. Preserve conditional commitments as conditional. A hypothetical prediction of Putin reacting to sanctions is not Putin speaking and is not automatically a US policy endorsement. Flag doubtful effectiveness-versus-endorsement cases together for adjudication.
4. Use the event/delivery date, not retrieval time. Apply actor/lens temporal bounds and preserve source institution and communication stream. No annual position follows from a couple of speeches.
5. Keep originals and exact character positions unchanged. Aligned reading aids can join lines and omit verified headers, with source indices retained. Uncertain word spacing, interrupted turns and incomplete claims stay quarantined; never guess a correction or stance.
6. French assisted review is recorded as assisted, not independent language validation. Machine translation, if later used, must be a separately attributed aid and cannot replace original offsets. No machine translation has been generated. Turkish unofficial/courtesy English versions retain their qualifications and missing-original limits.
7. EU institutional representation and EU common-position eligibility are separate. The verified Charles Michel role does not by itself clear every passage for institutional scoring.

## Provenance and scoring

All 21 prior judgments remain Badr_A-reviewed, AI-assisted and non-independent. Revision and exact-evidence transfer links count as one current review family, not extra human votes. There are 15 current families: five support, seven no_stance and three unresolved for strict territorial scope. B05-R1 separately retains support with W1 exclusion and its prior reason. Nothing in this consolidation silently relabels it.

AI draft labels have origin ai_generated, review_status unreviewed, no annotator ID, no independent-human status and no confidence/probability. A frozen assistant decision map makes this one pass replayable; it is not a trained classifier or repeated independent annotation. Human response fields begin blank. Reviewing visible suggestions is assisted and non-independent. Existing annotations, AI suggestions, source eligibility, evidence quality, model outputs and scoring ledgers remain separate.

No suggestion is training-approved or scoring-eligible. No current human judgment automatically clears source/language/scope gates. Evaluation requires separate independent judgments without suggestions or prior labels. Do not reuse an exposed annotator as an independent evaluator on the same event.
