# Experimental component proposal 1.0.0

Status: **proposed production protocol**, with AI-generated experimental component suggestions for new development evidence authorized by Badr's clarification on 24 October 2026. Existing approved strict labels, `consolidated-v1`, W1, approvals and public scores are unchanged. Definition file: `configs/proposals/components-v1.json`.

Retaining relevant evidence and approving a supervised strict-target label are different decisions. Source-cleared, attributable Ukraine-specific evidence may answer part of a lens while leaving the full target unsettled. Such evidence enters a distinct **component-evidence queue**; extraction, source, language and attribution defects remain technical holds. Unrelated material remains rejected. No actor's reputation, supposed intentions, silence or abstention supplies missing evidence.

## Fields and interpretation

| Dimension | Values / rule |
|---|---|
| Direction | support, oppose, mixed, no_stance, unresolved, relative to the named component. Mixed requires contradictory commitments at the same time/scope, not merely a condition. |
| Expression | explicit or contextually_implied; preserve the exact textual basis and linked paragraph/context. Synonyms and clear referents count; keyword matches alone do not. |
| Scope | comprehensive, specified_or_limited, unspecified. Preserve named territories/measures; specificity is not strength. |
| Conditions | Preserve timing, recipient, permitted use, phase, reciprocity and lifting/negotiation conditions in source wording. A restriction on one measure does not imply opposition to all measures. |
| Quality | Source provenance/clearance, speaker and institution, language/translation, extraction/offset integrity, event/copy/split checks. These are independent of political direction and missing scope. |

| Lens | Component structure |
|---|---|
| Territory | Sovereignty/integrity direction; territorial extent; recognition/non-recognition of annexation plus named annexation object. Recognition of separatist entities as states is distinct from recognition of incorporation into Russia. |
| Withdrawal | Withdrawal direction; territorial extent/line; timing and conditions. Comprehensive strict support continues to require W1. |
| Military assistance | Overall direction; specific assistance/measure position; type, recipient, time, permitted use and conditions. Humanitarian aid and direct combat deployment remain distinct. |
| Sanctions | Overall direction; specific measure/implementation position; Russia target, Ukraine basis and removal conditions. Effectiveness claims, economic costs, nonparticipation and legal implementation alone do not establish overall endorsement/opposition. |
| Responsibility | Direction on responsibility for initiating the February 2022 invasion; responsible actor and causal qualification. Economic effects, prior history and particular incidents remain different targets. |

## Illustrative mappings — examples, not new human judgments

| Source language | Experimental components | Existing strict target |
|---|---|---|
| “We reaffirm Ukraine's sovereignty and territorial integrity.” | Integrity support, explicit; extent unspecified; annexation not addressed. | Partial evidence, not automatic strict support. |
| “We will not recognize Russia's annexation of Crimea.” | Annexation non-recognition for Crimea; integrity support contextually implied if the Ukraine link is established. | Named scope cannot silently become all recognized Ukrainian territory. |
| “Russia must withdraw from Ukrainian territory.” | Withdrawal support, explicit; territorial extent unspecified. | W1 scope hold remains. B05-R1's history/hold stays unchanged. |
| “We urge all parties to pursue peace.” | No withdrawal commitment established. | No withdrawal stance inferred. |
| “We will continue equipping Ukraine to defend itself.” | Military-assistance support; expression contextually implied by equipping/defence; preserve type if specified. | Can meet the aid target when local context establishes military equipment and attributable commitment; exact phrase is unnecessary. |
| “We support Ukraine but will not send combat troops.” | Preserve separate aid and troop-deployment positions; aid not established by this sentence alone. | Do not label mixed merely because deployment is limited. |
| “These Russia-related measures over Ukraine will remain until withdrawal.” | Sanctions support, contextual referent explicit in linked context; conditional maintenance. | Conditions do not automatically mean mixed/opposition. |
| “We have sent humanitarian supplies.” | Humanitarian evidence, outside military-aid component. | Not military assistance. |

## Affected development records and migration

`territorial_affected_records.csv/json` lists **all 376 old development IDs** carrying partial territorial scope, with overlapping holds retained. The initial audit found 180 with a Ukraine-integrity textual cue and no other old hold; that is an acquisition-screening count, not 180 approved component labels. Other old records still need attribution, boundaries or language clearance. The new component packet identifies every selected original candidate through `derived_from_candidate_id`, its own versioned component ID, exact source hash/offsets, scope flags and experimental suggestion. Old auxiliary UK evidence remains indexed separately; the supplemental focal review does not restart bulk UK annotation.

Previously reviewed affected families include R-045f1cfa0f8e (EU), R-eefa9f146258 (Türkiye), R-5e8e011b84e9 and R-b69fa3f78fb1 (USA), R-7c4526d71289 (South Africa), with B09-R1/B10-R1/V2-B05 in historical lineage. No previous judgment or translation qualification is replaced. The component supplement is **new tasks only**, not another return of the 113 completed reviews.

If approved for production: publish a new codebook/schema version; add component annotations append-only; retain strict labels and their original codebook; migrate by exact ID/source/span mapping; require review when evidence/meaning changes; record explicit training permission separately. Do not transfer the old strict human label into a different component. Newly reserved groups remain untouched and never enter development exports. No training on experimental unreviewed suggestions.

## Future aggregation proposal — separate from public scoring

After review and validation, aggregate **each component separately** using the existing equal-claim → event → quarter hierarchy, deduplicating copied/overlapping claims and shared joint events. Report supportive/opposing/mixed direction distributions, event/period coverage and missingness rather than assigning arbitrary statement strengths. Report extent and annexation coverage beside integrity direction; do not average specificity into direction. No_stance, missing and unresolved contribute no neutral political value.

For uncertainty, resample independent event/leakage groups and report small-sample limits. Compare explicit-only and explicit-plus-contextually-implied evidence as a prespecified sensitivity analysis. Require minimum coverage and held-out, independently human-reviewed evaluation before an alignment mapping or calibrated score. Targeted acquisition cannot estimate annual country positions without a separate sampling design. These changes do not alter current published scores.

## Decisions together

| Decision | Recommended proposal | Consequence |
|---|---|---|
| Adopt component fields as the production annotation protocol? | Keep strict outputs/W1 and add versioned component fields with review. | Makes partial diplomatic positions usable for their actual component; no automatic strict-label migration or release scoring. |
| Future treatment of implied evidence? | Preserve expression and exact basis; primary explicit-only report plus sensitivity including reviewed implied evidence. | Prevents unsupported inference and shows how much interpretation affects conclusions. |
| Broaden EU institutional scope? | **No change** in this increment. Hold unmandated Commission comments and non-executive positions separately. | Source eligibility remains independent of substantive component relevance. |
