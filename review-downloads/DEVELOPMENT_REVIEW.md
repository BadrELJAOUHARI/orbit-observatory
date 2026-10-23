# Resumable development review

23 October 2026. This is the current review interface. It supersedes the mixed 184-row review export for active development review; old files remain immutable audit artifacts. No collection expansion is needed to use it.

## Contents and separation

The new standalone HTML and CSV contain only the five development_only events: 68 records, including 23 mechanically clean records and 45 quarantined records. Seven have previous judgments. The default Unreviewed + Mechanically clean filters show 21 records. Filtering does not change the export population: the returned CSV always contains all 68 development rows.

All 116 evaluation-event records, their passages, context, IDs and source URLs are absent from the development packet. The separate 21-item blind rehearsal remains unchanged. Generation verifies the frozen original queue hash and the event split before selecting development rows. Original candidate/row IDs, exact evidence offsets, prior annotation IDs/labels/reasoning, source/evidence flags, AI suggestions and assisted provenance are unchanged. No new judgment is created by producing or browser-testing this file.

## Review and resume

1. Download orbit-development-review.html from the private GitHub download branch using Download raw, then open the downloaded file in your browser. Do not try to review GitHub's HTML source display.
2. Enter your annotator ID once in the top bar. It fills a blank per-record ID when you select a label; it never changes prior annotations. Use the Unreviewed/Reviewed/All and Mechanically clean/Quarantined/All filters independently. A record becomes newly reviewed only after a label, annotator ID and reasoning are present. Notes do not disappear while you type.
3. Every edit automatically saves response fields and filter settings to localStorage. The saved-status indicator reports success, restoration, or a storage failure. No source text or previous labels are edited. This review remains AI-assisted and non-independent.
4. Keep the same browser profile and file location to resume automatically. Moving/renaming a local HTML file, switching browsers, clearing browser data or private browsing can change storage availability. Export progress backup (JSON) before doing so. CSV export also preserves all response fields and all development records.
5. Import either the exported CSV or progress JSON to resume elsewhere. Packet IDs, candidate IDs, field values and read-only evidence/history are checked before applying anything. Import is atomic. Different saved responses cause an error unless you explicitly enable replacement; an import never silently overwrites conflicting local work. Storage failure still permits backup/CSV export.
6. Return the exported CSV after reviewing the clean records; leave other rows present. Source, text, attribution and scope decisions have separate controls. Quality-only responses and deferral notes can be saved without assigning a stance. No small batches are needed.

Saving is local to your browser, not a remote submission. CSV/JSON backups are the portable recovery mechanism. Do not hand this assisted development file to independent blind annotators.

## Commands and outputs

From /workspace/orbit-observatory/orbit-observatory:

    PYTHONPATH=python python -m orbit_data.development_review
    PYTHONPATH=python python -m unittest discover -s tests -v
    PYTHONPATH=python python tests/browser_development_review.py
    PYTHONPATH=python python -m orbit_data.review_import /path/to/returned.csv --review-id development-review-0001

Outputs are in the outer ignored .local/development-review-v2 directory: orbit-development-review.html, orbit-development-review.csv, review_queue.json and manifest.json. Public metadata is workflow/development-v2/manifest.json. The importer auto-detects the protected development-only baseline; old mixed and blind returns remain supported under their original contracts. Future review records are append-only; original judgments and flags survive. Browser save/export does not itself import or approve a training label.

The standalone script is python/orbit_data/ui/development_review.js. The storage key includes the packet's exact SHA-256 identity, keeping responses separate from other datasets and from blind packets. Only mutable human responses and UI settings are saved. Evaluation passages are not embedded in HTML, CSV, progress JSON or exported responses.

## Verification and technical work

All 62 Python tests pass. Browser checks cover the 68-row development population, 21 initial visible records, quality/status filters, saved status, editable notes, CSV/JSON import/export, evidence/provenance protection, conflicting imports, explicit replacement, storage denial and manual backup fallback. Synthetic decisions were retained only in /tmp browser profiles and exports, never imported as research judgments.

Reload and a full browser-profile restart restore the entered decision and notes. The exported CSV payload after restart matches the original export exactly. Actual CSV downloads and JSON/CSV round trips were also checked in fresh browser contexts. The environment's managed Chromium crashes in its persistent-profile download handler (NSS database initialization), so the restart test captures the exported Blob before download; this is a browser-test limitation, not a claim that that download path passed. These checks used a local HTTP origin because the managed browser blocks file URLs. Local-file storage is browser-dependent and the UI reports failure rather than claiming a save succeeded.

The development packet is frozen while Badr reviews it. Technical source clearance and future collection use separate versioned artifacts; new sources must not silently replace this packet or invalidate its saved responses. No expansion, model fitting, public-score update or website redesign occurred in this interface task. Next technical milestone is source/language eligibility clearance and separately versioned collection expansion, not another annotation batch.
