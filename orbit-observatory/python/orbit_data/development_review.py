"""Development-only resumable review, preserving the frozen consolidated corpus."""
import json
from pathlib import Path
from collections import Counter
from .validation import ROOT,digest
from .workflow import save_text_immutable,write_csv,QUALITY_RESPONSE_OPTIONS
from .reviewed import write_immutable

VERSION='development-review-2.0.0'
OUTPUT=ROOT.parent/'.local/development-review-v2'
RESPONSE_FIELDS=('human_label','human_annotator_id','human_review_notes','human_independent',*QUALITY_RESPONSE_OPTIONS)


def development_rows(rows,split):
    selected=[dict(row) for row in rows if row['event_role']=='development_only']
    if not selected:raise ValueError('No development records')
    if len({r['candidate_id'] for r in selected})!=len(selected):raise ValueError('Duplicate development candidate')
    if len({r['row_id'] for r in selected})!=len(selected):raise ValueError('Duplicate development row ID')
    for row in selected:
        if split['event_roles'].get(row['event_id'])!='development_only' or row['event_id'] in split['reserved_event_ids']:
            raise ValueError('Evaluation event cannot enter development export')
        if row['human_independent']!='false':raise ValueError('Development review must remain assisted/non-independent')
    return selected


def render(path,rows,packet):
    import html
    esc=lambda v:html.escape(str(v),quote=True)
    payload=json.dumps(dict(packet_id=packet,version=VERSION,response_fields=RESPONSE_FIELDS,rows=rows),ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    css='''body{font:16px/1.5 system-ui;max-width:1100px;margin:1.5rem auto;padding:0 1rem;background:#f4f6f8;color:#17202a}article{background:#fff;border:1px solid #c8cfd7;border-radius:8px;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.5 system-ui}label{display:block;margin:.5rem 0}select,input,textarea,button{font:inherit;padding:.4rem}textarea{width:95%;min-height:5rem}button{margin:.3rem}.controls{position:sticky;top:0;background:#f4f6f8;border-bottom:1px solid #bcc6d0;padding:.5rem;z-index:2}.filters{display:flex;flex-wrap:wrap;gap:1rem}.draft{background:#fff3cb;padding:.7rem}.flag{color:#823d0a}small{overflow-wrap:anywhere}.ok{color:#185b24}.error{color:#a11919}article[hidden]{display:none}.muted{color:#536171}summary{cursor:pointer}'''
    parts=[f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ORBIT development review</title><style>{css}</style>',
        '<h1>ORBIT development review</h1><p>Development events only. Your review remains AI-assisted and non-independent. Prior judgments and unreviewed AI suggestions stay separate from your responses.</p>',
        '<p>Read the exact proposition and source passage with context. Source eligibility, attribution, scope and text quality have separate response fields. Quarantine is not a stance label.</p>',
        '<div class="controls"><div class="filters"><label>Review status <select id="status-filter"><option value="unreviewed">Unreviewed</option><option value="all">All review states</option><option value="reviewed">Reviewed</option></select></label>',
        '<label>Evidence quality <select id="quality-filter"><option value="clean">Mechanically clean</option><option value="all">All qualities</option><option value="quarantined">Quarantined</option></select></label>',
        ''.join('<label>'+esc(label)+' <select id="'+name+'"><option value="">All</option>'+''.join('<option value="'+esc(v)+'">'+esc(v)+'</option>' for v in sorted({str(row.get(field,''))[:4] if field=='event_date' else str(row.get(field,'')) for row in rows}) if v)+'</select></label>' for name,label,field in [('actor-filter','Actor','actor_id'),('lens-filter','Lens','lens_id'),('period-filter','Year','event_date'),('label-filter','Proposed label','ai_suggested_label')]),
        '<label>Search <input id="search" aria-label="Search development review"></label><label>Annotator ID <input id="annotator" placeholder="Enter your ID once"></label></div>',
        '<p id="count" aria-live="polite"></p><p id="save-status" role="status" aria-live="polite">Checking saved progress…</p>',
        '<button id="export-csv">Export review CSV</button><button id="export-json">Export progress backup</button><button id="import-button">Import CSV / progress backup</button><input type="file" id="import-file" accept=".csv,.json" hidden>',
        '<label><input type="checkbox" id="allow-replace"> Allow imported responses to replace different local responses</label>',
        '<p id="import-status" role="status" aria-live="polite"></p></div>',
        '<p class="muted">Edits save automatically in this browser. Keep the same file location. Before moving the file, switching browsers or clearing browser data, export a backup. Import it to resume elsewhere. Export always includes every development row, regardless of filters.</p><main>']
    for i,row in enumerate(rows):
        parts.append(f'<article data-index="{i}" id="{esc(row["row_id"])}"><h2>{esc(row["row_id"])} · {esc(row["actor_id"])} · {esc(row["event_date"])}</h2><p><b>Proposition:</b> {esc(row["lens_proposition"])}</p>')
        parts.append(f'<p>Selection: {esc(row["selection_kind"])} · Event: {esc(row["event_id"])} · <b>{"Quarantined" if row["quarantine"]=="true" else "Mechanically clean"}</b></p><p class="flag">{esc(row["quality_flags"])}</p>')
        parts.append(f'<small>Candidate {esc(row["candidate_id"])} · offsets [{row["start"]}, {row["end"]}) · language {esc(row["language"])} · <a href="{esc(row["source_url"])}" target="_blank" rel="noopener">Official source</a></small><p>{esc(row["source_qualification"])}</p>')
        parts.append(f'<details><summary>Context before</summary><pre>{esc(row["context_before"])}</pre></details><h3>Exact stored passage</h3><pre>{esc(row["exact_passage"])}</pre><details><summary>Aligned reading aid</summary><pre>{esc(row["reading_text"])}</pre></details><details><summary>Context after</summary><pre>{esc(row["context_after"])}</pre></details>')
        if row['existing_annotation_id']:
            parts.append(f'<div class="previous"><b>Previous judgment: {esc(row["existing_label"])}</b><p>{esc(row["existing_provenance"])}</p><p>{esc(row["existing_review_notes"])}</p></div>')
        if row['ai_suggested_label']:
            parts.append(f'<div class="draft"><b>AI-generated, unreviewed suggestion: {esc(row["ai_suggested_label"])}</b><p>{esc(row["ai_rationale"])}</p><small>{esc(row["ai_review_flags"])}</small></div>')
        choices=''.join(f'<option value="{v}">{v or "Leave blank"}</option>' for v in ('','support','oppose','no_stance','mixed','unresolved','not_applicable'))
        parts.append(f'<label>Your label <select data-field="human_label">{choices}</select></label><label>Annotator ID <input data-field="human_annotator_id"></label><label>Reasoning / review notes <textarea data-field="human_review_notes"></textarea></label>')
        parts.append('<details><summary>Separate source, text, attribution and scope responses</summary>')
        for field,values in QUALITY_RESPONSE_OPTIONS.items():
            choices=''.join(f'<option value="{v}">{v or "Leave blank"}</option>' for v in ('',)+values)
            parts.append(f'<label>{esc(field.replace("human_", "").replace("_", " "))}<select data-field="{field}">{choices}</select></label>')
        parts.append('</details><p class="muted">Assisted review. Existing records are never overwritten by this file; returned decisions are imported as new provenance-linked records.</p></article>')
    parts.append('</main><script type="application/json" id="packet-data">'+payload+'</script><script>')
    parts.append((Path(__file__).parent/'ui/development_review.js').read_text())
    parts.append('</script></html>')
    save_text_immutable(path,''.join(parts))


def build():
    source=ROOT.parent/'.local/workflow-v1/review_queue.json'
    source_manifest=json.loads((source.parent/'manifest.json').read_text())
    if digest(source.read_bytes())!=source_manifest['artifacts']['review_queue.json']:
        raise ValueError('Frozen consolidated source export changed')
    split=json.loads((ROOT/'workflow/v1/event_split.json').read_text())
    original=json.loads(source.read_text())
    rows=development_rows(original,split)
    packet=digest(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode())
    write_immutable(OUTPUT/'review_queue.json',rows)
    write_csv(OUTPUT/'orbit-development-review.csv',rows)
    render(OUTPUT/'orbit-development-review.html',rows,packet)
    manifest=dict(version=VERSION,packet_id=packet,records=len(rows),events=sorted({r['event_id'] for r in rows}),
        mechanically_clean=sum(r['quarantine']=='false' for r in rows),quarantined=sum(r['quarantine']=='true' for r in rows),
        previously_reviewed=sum(bool(r['existing_annotation_id']) for r in rows),
        unreviewed_clean=sum(r['quarantine']=='false' and not r['existing_annotation_id'] for r in rows),
        evaluation_records=0,assisted=True,independent_human=False,
        input_sha256=digest(source.read_bytes()),event_split_sha256=digest((ROOT/'workflow/v1/event_split.json').read_bytes()),
        files={name:digest((OUTPUT/name).read_bytes()) for name in ('review_queue.json','orbit-development-review.csv','orbit-development-review.html')})
    write_immutable(OUTPUT/'manifest.json',manifest)
    write_immutable(ROOT/'workflow/development-v2/manifest.json',manifest)
    print(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':build()
