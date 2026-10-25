# Adopted protocol and one consolidated review

Protocol: codebooks/components-v2.0.0/README.md and protocol.json. User authorized adoption, with explicit synonyms and linked-context implication clarified. No remaining substantive decision blocks annotation. Public quantification/calibration and minimum coverage thresholds still require validation before release; this change does not approve them.

Inventory: 780 distinct task identities (561 earlier strict + 48 supplementary strict + 171 component). Zero duplicate task identities removed; 694 exact passages are grouped once with linked tasks. Strict and component tasks remain separate, preserving candidate IDs, event IDs, original offsets and revision links. There are 348 event IDs / 327 conservative leakage groups. Evaluation records are excluded. Earlier 113 completed reviews are outside this workload and remain untouched.

Outstanding on the server: 780 tasks, 609 strict outputs and 171 component task bundles, zero completed returns found for these IDs. Each bundle now has independently blank component fields; it is not 171 preapproved generic territorial labels. Exact completed counts on your browser are unknown until you import saved responses. The interface shows tasks with saved input; that count is not completed/adjudicated labels.

Open review.html. Shared passages appear once; fill separate integrity, annexation, expression, extent, condition and quality responses as applicable. Aid/sanctions also have separate overall and measure directions. You may leave unrelated axes blank. Strict outputs remain optional and distinct. Enter annotator ID and reasoning; export the full CSV plus a JSON backup before moving browsers or files. No collection rerun is needed.

Import old packet CSV/JSON backups through the same entry point. Existing strict responses resume as strict responses. Earlier generic experimental component responses are retained verbatim as prior-response history, not silently promoted to new axes. Legacy browser keys can be recovered automatically only on the same browser origin; otherwise use portable imports. Conflicts require explicit replacement. Imported history also survives the consolidated CSV and progress backup. Old packets and storage keys are preserved.

Return validator:

```bash
PYTHONPATH=python python -m orbit_data.protocol_v2 --import-csv /path/to/returned.csv
```

It checks all 780 IDs, immutable evidence and independent component enums, then verifies original text hashes/offsets. It appends assisted, nonblind review records; it grants no training authorization. The record/component-scoped eligibility function accepts a reviewed, explicitly authorized integrity/withdrawal/etc. label despite missing unrelated full-target components, while preserving source/language/attribution holds and evaluation exclusion. No fit command is invoked.

Use a loopback server if your browser restricts local files: `python -m http.server 8765 --bind 127.0.0.1` in the extracted packet, then open http://127.0.0.1:8765/review.html. Autosave is origin/location dependent; portable backups are the cross-browser guarantee.

With a future explicit approval file (not created or granted in this task), `--export-approved /path/to/approval.json` freezes only already-returned labels for named candidate/component pairs. Its format is `{"protocol":"components-v2.0.0","approved_by":"Badr_A","approvals":{"ACTUAL_CANDIDATE_ID":["integrity_direction"]}}`. The exporter preserves assistance, excludes unreviewed/conflicting labels and source holds, retains event/copy groups and writes inclusion/exclusion files with null alignment scores. Annexation may remain blank while an approved integrity label is usable. The command never trains. Free-text conditions remain attached review metadata, not invented numerical targets.
