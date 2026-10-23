# ORBIT — Strategic Narrative Observatory

First functional evidence prototype: Russia and Ukraine are positional anchors; USA and EU are tracked actors. Genuine Three.js 3D scene, orbit controls, timeline, actor filters, hover cards, evidence dossiers, original-source links and JSON export.

## Run locally

From this folder run `python -m http.server 8000 --directory dist` and open http://localhost:8000. Internet access is used only for optional Google Fonts; the Three.js runtime is bundled locally.

## Data

Run `python python/build_data.py` to rebuild the curated dataset. Optional `python python/collect_transcripts.py` collects two public-domain US transcripts; then rebuild data. Six selected documents, 2014/2022/2024/2025. Other years are unscored. Source labels are editorial annotations made for this prototype and have not been independently reviewed. There is no trained ML model in this release and no estimated confidence. All selected documents have +1 labels. No artificial annual variation or interpolation.

## Measurement

Lens: expressed support for Ukrainian sovereignty and territorial integrity. Documents differ in specificity; notably the 2025 US statement affirms sovereignty without settling precise territorial questions. This coarse initial coding is shown with that limitation. Equal-weight document mean; x=6*mean, anchors at x=-9/+9. y/z and radius are decorative. Missing evidence uses a separate unscored lane. EU represents institutional rhetoric, not all member states separately.

## Next implementation

Expand the corpus; separate sovereignty from exact-border and other policy propositions; independently annotate passages with offsets; evaluate a Python transformer classifier on held-out documents and years; report calibration and coverage before replacing editorial scores. Add Israel–Palestine as a separate universe with its own sources and operational definitions.

## Verification

JavaScript syntax and data assertions checked. Browser visual/interaction QA was unavailable in the build environment. No automatic collection completeness claims. 2026 is partial through 10 October 2026 and has no records yet.
