# ORBIT implementation handoff

Updated 22 October 2026. Read this before the methodology: later user decisions below supersede its first-lens-only release scope.

## User and purpose
Badr is building a computational politics portfolio for HCSS and learning Python/NLP. He knows basic Python; explain transformer concepts, data collection and implementation decisions step by step. Work in manageable increments, persist working outputs, and keep a development log. Avoid em dashes in new prose.

## Approved product scope
Develop a substantial first release, not a minimal demo. Universe: Russia–Ukraine. Five displayed actors: United States, European Union, Türkiye, India, South Africa. EU is an institutional actor. Russia and Ukraine are reference poles, not additional tracked planets. Future Israel–Palestine is deferred.

All FIVE lenses are required for first release: territorial recognition, Russian troop withdrawal, military assistance to Ukraine, sanctions against Russia, responsibility for the February 2022 full-scale invasion. The last lens is inapplicable before 2022. Desired timeline: 2012–2026, with nulls for insufficient evidence and explicit partial-year cutoff. Never invent changes just to make the animation interesting.

Preserve the approved visual identity, logo, landing page, central large 3D scene, black holes, planets, timeline, right-side controls and dossier style. Planet labels should be compact names/markers without permanent information boxes; details appear on hover and click. Implement features within that design. Do not rebuild the website from a generic template.

## Measurement decisions
The user explicitly approved the hierarchical weighting approach. For each actor, lens and window: deduplicate mirrors/translations into communication events; collapse repeated identical claims within an event; give distinct eligible claims equal shares of their event; give eligible events equal shares of their quarter; give covered quarters equal shares of the annual/window budget. Full-year coverage requirements remain provisional pilot gates in the methodology.

For a stance-bearing claim, calibrated support probability p gives s=2p-1. No stance and unresolved attribution are distinct outcomes. Event score is the mean of eligible distinct claim scores. If Q quarters are covered and quarter q has n_q eligible events, event weight is a_e=1/(Q*n_q). Annual/window score S=sum(a_e*s_e). Claim contributions are a_e*s_i/m_e and sum to S. Publish all weights and inclusion rules. Do not multiply again by model confidence or weight by document length, GDP or arbitrary official prestige.

Use fixed, explicitly defined policy references for longitudinal comparisons. On a single lens d_U=(1-S)/2 and d_R=(1+S)/2. These are policy-axis distances, not alliance probabilities or actual gravitational physics. Reconcile numeric coordinates with existing decorative offsets explicitly. Negotiation language alone is not pro-Russia. Generic sovereignty language does not automatically establish a precise territorial position.

Separate missing coverage, model ambiguity, event disagreement and cross-lens divergence. Unscored is not neutral. Preserve original source offsets for highlights. A composite advanced view is in scope, but must have justified dimensions, published weights, overlap checks and a fixed missing-data policy; do not silently renormalize missing dimensions. Full formulas and literature references are in docs/ORBIT_Methodology_v0_1.qmd.

## Required functional scope
Official-source acquisition and provenance; deduplication; claim annotation and review; a simple classifier baseline; a fine-tuned pretrained transformer; held-out event/time evaluation; probability calibration; aggregate accuracy; hierarchical scoring; uncertainty and sensitivity calculations; all five lens filters; source dossiers and authentic highlights; period comparison; weight-sensitivity controls; advanced profile/composite view; reproducible scripts and documentation.

A stage-by-stage build is accepted, but the release target includes all five lenses. Do not describe incomplete scaffolding as a finished research application. Fine-tune a pretrained transformer; training a language model from scratch is not required. Identify compute needs before promising a training run. Store datasets and model checkpoints to avoid rerunning everything.

## Actual existing implementation
This archive contains the local source checkpoint b043d73 (Update Site source). The source folder had no configured Git remote when checked. It is not confirmed to exist in the user's GitHub account.

Frontend: dist/index.html, dist/app.js, dist/style.css, bundled Three.js and OrbitControls. These files are the editable website, despite the dist folder name. Python: python/build_data.py and python/collect_transcripts.py. Data: six curated official documents spanning 2014, 2022, 2024 and 2025, with one locally stored transcript. All selected scores are editorial +1. No trained ML model or validated confidence estimates exist. The current aggregation is a coarse document mean, NOT the newly approved hierarchical method. Audit and replace the measurement layer; preserve the visual.

Run the current scene from repository root:
python -m http.server 8000 --directory dist

Site reference: https://orbit-strategic-observatory.sandyocean4.chatgpt.site
Sites project identifier: appgprj_6aca00fdaa488191963c108b764b25fd
This archive does not automatically transfer hosting permissions, environment state or the full previous chat.

## First task for the new session
1. Read AGENTS.md, this handoff, the methodology and existing README.
2. Inspect the source and run the current site. Identify factual limitations and preserve a visual checkpoint.
3. Create a staged implementation plan covering all five lenses and five actors, with clear acceptance criteria. Record it in docs/IMPLEMENTATION_PLAN.md.
4. Set up Python project structure, dependencies, versioned lens/source configuration and schemas. Preserve the existing scene.
5. Implement the first official-source collection and provenance workflow. Begin with a small auditable sample, then expand. Do not train on unreviewed invented labels.
6. Report what changed, how it was checked, what is blocked, and what Badr should learn next. Save progress in docs/PROGRESS.md.

Use documented official sources; preserve URL, issuer, event date, retrieval date, language, text hash and offsets. Keep event clusters and translations together across splits. Scope EU to common institutional positions as specified in the methodology. Inspect terms and access restrictions before collection, use caching and respectful request rates. Never put credentials into the repository. Do not claim training, evaluation or deployment succeeded without executing and checking it.
