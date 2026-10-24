# First annotation review and private source preservation

The codebooks are frozen at [version 1.0.0](../codebooks/v1.0.0/README.md) for this diagnostic batch. Their five sheets define support, oppose, no_stance, mixed and unresolved, plus the administrative not_applicable state. Frozen does not mean empirically validated: actual independent human coding may require a new version.

## Your first batch

The local, private review files are outside the application checkout, under /workspace/orbit-observatory/.local/annotation-v1/:

- first_batch.md: readable context and exact passages for B01–B25.
- first_batch.csv and first_batch.jsonl: editable return formats, 20 retrieved candidates plus 5 random controls.
- queue.csv and queue.jsonl: all 184 original passage/lens candidates, representing 171 distinct passages and ten communication events.
- manifest.json: source/codebook hashes, artifact hashes, selection IDs, counts and random-control populations. No human or machine labels are present.

Read the common codebook, then open first_batch.md. Make your own copy of first_batch.csv, for example Badr_A_first_batch.csv. Import as UTF-8 text with comma separation and quoted multiline cells; avoid spreadsheet auto-formatting or formula interpretation of source text. JSONL is an alternative if your editor preserves it more reliably.

Fill only these four columns:

| Column | What to enter |
| --- | --- |
| label | support, oppose, no_stance, mixed, unresolved or not_applicable; blank if undecided |
| annotator_id | Your own stable ID, such as Badr_A |
| review_status | annotated for a decision; needs_adjudication for substantive ambiguity; needs_language_review with a blank label if you cannot read the source language |
| review_notes | Speaker, target/scope, conditions, proposed claim split/expanded source span and reasons for uncertainty; required for mixed/unresolved or language deferral |

Keep all rows and all other columns unchanged, even for partial returns. Save UTF-8 CSV/JSONL and attach the edited copy to this chat. A partial first pass is useful; empty labels are not errors in a draft. For the French row, use the original or defer it. There is no machine translation or suggested label to copy. Do not read the assistant's lens-screen conclusions before making independent judgments.

The same passage appears under different propositions, including B02/B03. Its passage_id links those tasks; event_id remains unchanged. Label each proposition separately. This is not duplicate event evidence. If the exact line cannot support a decision without additional decisive text, note a proposed expanded span rather than silently labeling evidence outside it.

B01–B20 span every actor, lens and source document and deliberately include difficult attribution/scope cases. They are not an evaluation sample. B21–B25 are seeded random non-retrieved controls, one per actor. Sampling seed is 20261023; eligible non-retrieved line populations are USA 83, EU 291, TUR 455, IND 208 and ZAF 244. These controls begin a missed-evidence audit; five observations do not estimate retrieval recall. Judge the assigned proposition and note other potentially missed policy claims. Context may overlap retrieved material, so distinguish the central non-retrieved line from context.

Independent annotation means a second real human uses a fresh blank copy and their own ID without seeing the first person's labels or assistant screens. Preserve both versions, compare disagreements, then adjudicate in a separate record. A repeated model call or a second pass by the same person does not supply an independent annotator. No independent annotations have been generated here.

## Commands and validation

From /workspace/orbit-observatory/orbit-observatory:

    PYTHONPATH=python python -m orbit_data.annotations prepare
    PYTHONPATH=python python -m orbit_data.annotations validate
    PYTHONPATH=python python -m orbit_data.annotations validate --kind queue
    PYTHONPATH=python python -m orbit_data.annotations validate --file /path/to/Badr_A_first_batch.csv
    PYTHONPATH=python python -m unittest discover -s tests -v

The validator rebuilds references from the frozen corpus, checks schema/IDs/events, hashes and exact offsets/context, rejects unknown or duplicate/dropped rows, and permits edits only in the four human columns. A label requires an annotator ID and status. Mixed/unresolved require notes. Language deferral must retain an empty label. Use --completed only when all rows should have final first-pass decisions; it rejects pending/deferred/adjudication rows. Passing validation is not evidence of label accuracy or independent agreement.

Preparation refuses to overwrite any existing human edits, even notes or an annotator ID without a label. Store returned copies separately. This milestone validates preparation/returned task files; it does not automatically promote them to adjudicated claims or import them into training. A separate annotation schema version 1.1.0 supports mixed while preserving the original 1.0.0 record contract; origin remains human/editorial, never model. No filled canonical human-annotation records were created.

The frozen corpus's ten text hashes are pinned in annotations/v1/selection.json. Source changes require a new corpus/batch version rather than applying old offsets to new text. Full passages remain in the ignored private output rather than publicly versioned Git files. Versioned selection/manifest metadata contains references, hashes and counts only.

## What is actually retained now

The ten normalized documents and their corresponding original response bytes from the preceding milestone are still present in this attached workspace. Every raw/text hash was checked again against the saved record metadata, and all 184 candidates' offsets still reproduce the same exact text. This verifies retention across these conversation turns in the current workspace.

It does not prove restoration into a new cloud task or a fresh machine. No tool available here starts a second environment to test that. Platform onboarding documentation describes publication as snapshotting the prepared filesystem, including installed files; live processes do not survive. Git ignores do not themselves prove exclusion from that snapshot. A current published base-version identifier is also not a restoration test. Publish the prepared environment through environment settings when retaining these files in its snapshot, and verify hashes in any new task before using returned annotations. Fresh-machine restoration remains unverified.

A Git clone alone will not restore .local/ files or these uncommitted changes. Do not rely on it for source preservation. The codebooks, schemas, manifest and metadata should be committed through the normal reviewed repository workflow; full texts are not being added to public Git here.

## Private portable backup and restore

A verified private archive is created at /workspace/orbit-observatory/.local/orbit-review-v1.tar.gz, with a SHA-256 sidecar. It contains the frozen raw/text cache, source/queue records, both annotation exports, codebooks, schema/configuration, collection/preparation code and review instructions. It excludes Git metadata, environment variables, credentials and unrelated workspace files. BUNDLE_MANIFEST.json hashes each included file. It is a private research/annotation handoff, not permission to redistribute source works.

Create/recreate it before making an external private backup:

    PYTHONPATH=python python -m orbit_data.annotations bundle

Download that archive and checksum to your own access-controlled storage if applicable source terms permit that storage. No remote storage service is connected or uploaded to automatically. A second copy on this same machine protects against accidental file edits, not loss of the machine. Any source whose external private storage is not permitted should be retained by manifest/metadata only and retrieved again through its official allowed route.

After verifying the archive checksum, extract it into a private directory. From its orbit-review-v1/application/ directory:

    python -m pip install -r requirements-data.txt
    PYTHONPATH=python python -m orbit_data.validate ../pilot-v1
    PYTHONPATH=python python -m orbit_data.annotations validate --cache ../pilot-v1 --output ../annotation-v1

All archive members were hash-verified; restoration into a temporary local directory and both record/annotation validation commands were exercised without network access to the sources. That tests archive portability on the current toolchain, not restoration by the cloud snapshot service on a fresh machine.

For reproducible retrieval without a stored full-text backup, retain source_manifest/, normalization/extraction code, pinned dependencies and document hashes. In a private new output directory, run the official collector and source checks, respecting the current robots/access rules:

    PYTHONPATH=python python -m orbit_data.collect --output /private/new-pilot

Compare every new normalized text hash with annotations/v1/selection.json before reusing offsets. A changed page/PDF is not the old evidence; keep it as a new version and recover the old snapshot from an allowed backup or flag it unavailable. Retrieval is reproducible as a procedure, not a guarantee that publishers will preserve identical bytes. Network permissions, removed sources or changed robots policies can prevent restoration; never bypass them.

UN redistribution/complete terms review remains unresolved, so full texts and annotation excerpts are kept local/private and not cleared for publication. The US government's copyright policy has exceptions for third-party works. This workflow preserves an allowed-route retrieval alternative and makes no blanket license claim. The French original remains unchanged; no translated text is being passed off as original evidence.
