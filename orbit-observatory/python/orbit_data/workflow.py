"""Consolidated, frozen-corpus review preparation, with separate AI suggestions."""
import csv
import html
import json
import random
import re
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator

from .annotations import read_rows, task
from .followup import overlay_history
from .resegment import layout_header_line, validate_export_references
from .review4 import validate_quality
from .validation import ROOT, digest, validate_dataset
from .reviewed import write_immutable

POLICY = json.loads((ROOT/'workflow/v1/policy.json').read_text())
SUGGESTION_VALIDATOR=Draft202012Validator(json.loads((ROOT/'schemas/suggestions-v1/suggestion.schema.json').read_text()))
QUALITY_RESPONSE_OPTIONS={
    'human_source_eligibility':('eligible','ineligible','needs_review'),
    'human_text_quality':('usable','defective','needs_review'),
    'human_attribution':('attributable','wrong_actor','needs_review'),
    'human_scope':('exact_target_met','partial_scope','no_relevant_stance','needs_review'),
}


def load_corpus():
    cache=ROOT.parent/'.local/pilot-v1'
    v1=ROOT.parent/'.local/annotation-v1'
    v2=ROOT.parent/'.local/annotation-v2'
    for directory in (v1,v2):
        manifest=json.loads((directory/'manifest.json').read_text())
        for name,sha in manifest['artifacts'].items():
            if digest((directory/name).read_bytes())!=sha:raise ValueError('Frozen artifact changed: '+name)
    base=json.loads((cache/'records.json').read_text())
    old=overlay_history(v1)
    candidates=json.loads((v2/'candidates.json').read_text())+json.loads((v2/'batch-0002/control_records.json').read_text())
    reviewed=json.loads((v2/'reviews/Badr_A/review-0004/overlay_records.json').read_text())
    assessments=json.loads((v2/'reviews/Badr_A/review-0004/quality_assessments.json').read_text())
    records=base+old+candidates+reviewed
    validate_dataset(records,cache)
    validate_quality(assessments,records)
    index={r['id']:r for r in records}
    texts={r['id']:(cache/r['text_path']).read_text() for r in base if r['record_type']=='document'}
    segments=json.loads((v2/'segments.json').read_text())
    transfers=json.loads((v2/'annotation_transfers.json').read_text())
    annotations={r['claim_id']:r for r in old+reviewed if r['record_type']=='annotation'}
    for transfer in transfers:
        annotations.setdefault(transfer['to_candidate_id'], index[transfer['from_annotation_id']])
    control_ids={c['id'] for c in json.loads((v2/'batch-0002/control_records.json').read_text())}
    return records,candidates,index,texts,segments,annotations,assessments,control_ids


def make_task(candidate,index,texts,segments,control_ids):
    doc=index[candidate['document_id']]
    text=texts[doc['id']]
    row=task(doc,index[candidate['event_id']],candidate,text,'R-'+candidate['id'][-12:],[])
    row['selection_kind']='nonretrieved_random_control' if candidate['id'] in control_ids else 'retrieved_candidate'
    us=segments[doc['id']]['units']
    before=[u for u in us if u['end']<=candidate['start']][-2:]
    after=[u for u in us if u['start']>=candidate['end']][:2]
    a=before[0]['start'] if before else candidate['start']
    b=after[-1]['end'] if after else candidate['end']
    row.update(context_start=a,context_end=b,context_before=text[a:candidate['start']],context_after=text[candidate['end']:b])
    return row


def screen(candidate,row,text,assessment=None):
    original=list(candidate['quality_issues'])
    flags=set(original)
    if assessment:flags.update(assessment['scope_flags'])
    resolutions=[]
    if 'extraction_header_in_envelope' in flags:
        indices=set(candidate['source_indices'])
        missing=[i for i in range(candidate['start'],candidate['end']) if i not in indices]
        masked=''.join(text[i] for i in missing)
        if (missing and all(layout_header_line(line) for line in masked.splitlines() if line.strip())
                and ''.join(' ' if text[i]=='\n' else text[i] for i in candidate['source_indices'])==candidate['reading_text']):
            flags.remove('extraction_header_in_envelope')
            resolutions.append('header_obstruction_resolved_by_exact_source_aligned_reading_view')
    suspect=[]
    for pattern in POLICY['suspect_word_patterns']:
        for m in re.finditer(pattern,text[row['context_start']:row['context_end']]):
            suspect.append(dict(start=row['context_start']+m.start(),end=row['context_start']+m.end(),text=m.group()))
    if suspect:flags.add('suspected_intraword_spacing_requires_source_comparison')
    reasons=sorted(f for f in flags if f in POLICY['source_quarantine_flags']
                   or f.startswith(POLICY['attribution_quarantine_prefix'])
                   or f in POLICY['unrepairable_text_flags']
                   or f in ('extraction_header_in_envelope','suspected_intraword_spacing_requires_source_comparison'))
    return dict(candidate_id=candidate['id'],original_flags=original,effective_flags=sorted(flags),
                quarantine=bool(reasons),quarantine_reasons=reasons,mechanical_resolutions=resolutions,
                suspect_source_spans=suspect,screen_origin='deterministic_quality_screen_not_stance_annotation',
                scoring_eligible=False)


def corpus_snapshot():
    records,candidates,index,texts,segments,annotations,assessments,control_ids=load_corpus()
    assess={a['candidate_id']:a for a in assessments}
    rows={c['id']:make_task(c,index,texts,segments,control_ids) for c in candidates}
    validate_export_references(list(rows.values()),records,texts)
    screenings={c['id']:screen(c,rows[c['id']],texts[c['document_id']],assess.get(c['id'])) for c in candidates}
    clean_pending=[c for c in candidates if not screenings[c['id']]['quarantine'] and c['id'] not in annotations]
    snapshot_sha=digest(json.dumps(dict(candidates=candidates,rows=rows,screenings=screenings),sort_keys=True,ensure_ascii=False).encode())
    return records,candidates,index,texts,segments,annotations,rows,screenings,clean_pending,snapshot_sha


def key(candidate):return f"{candidate['document_id']}:{candidate['start']}:{candidate['lens_id']}"


def evaluation_design(candidates,index,control_ids):
    rng=random.Random(POLICY['evaluation']['seed'])
    selected=[]
    for actor in sorted({index[c['document_id']]['actor_id'] for c in candidates}):
        events=sorted({c['event_id'] for c in candidates if index[c['document_id']]['actor_id']==actor})
        selected.append(rng.choice(events))
    sample=[]
    for event in selected:
        # Random, stratified across available lenses; do not select on AI labels.
        pool=sorted([c for c in candidates if c['event_id']==event],key=lambda c:c['id'])
        rng.shuffle(pool)
        chosen=[]
        for lens in sorted({c['lens_id'] for c in pool}):
            chosen.append(next(c for c in pool if c['lens_id']==lens))
        chosen=chosen[:POLICY['evaluation']['candidates_per_event']]
        sample.extend(c['id'] for c in chosen)
        # Preserve original retrieval controls in the blind sample where available.
        sample.extend(c['id'] for c in pool if c['id'] in control_ids and c['id'] not in sample)
    return dict(split_version='event-holdout-1.0.0',seed=POLICY['evaluation']['seed'],
                reserved_event_ids=selected,blind_candidate_ids=sample,
                event_roles={event:'evaluation_rehearsal' if event in selected else 'development_only'
                             for event in sorted({c['event_id'] for c in candidates})},
                excluded_from_training_and_tuning_event_ids=selected,
                final_evaluation_ready=False,prior_pilot_exposure=True,
                limitation='Pilot events informed codebook development and assisted review. This is a blind labeling rehearsal, not an untouched confirmatory test. Final evaluation needs new events and separate independent humans.')




def save_text_immutable(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_text()!=content:
        raise ValueError('Preserve existing export or reviewed work: '+str(path))
    if not path.exists():path.write_text(content,encoding='utf-8')


def csv_cell(value):
    if isinstance(value,bool):return str(value).lower()
    return '' if value is None else str(value)


def write_csv(path,rows):
    import io
    buffer=io.StringIO(newline='')
    writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader();writer.writerows({k:csv_cell(v) for k,v in row.items()} for row in rows)
    save_text_immutable(path,buffer.getvalue())


def priority(screening,suggestion,existing):
    tags=[]
    if screening['quarantine']:tags.append('source_attribution_or_text_problem')
    if any('scope' in f for f in screening['effective_flags']):tags.append('partial_scope')
    label=suggestion.get('label') if suggestion else existing.get('label') if existing else None
    if label in ('oppose','mixed','unresolved'):tags.append(label)
    if suggestion and suggestion['review_flags']:tags.extend(suggestion['review_flags'])
    rank=100 if screening['quarantine'] else 95 if 'partial_scope' in tags else 90 if label in ('oppose','mixed') else 80 if label=='unresolved' else 60 if tags else 20 if not existing else 10
    return rank,';'.join(tags) or ('already_recorded' if existing else 'routine_check')


def render_html(path,rows,*,blind=False):
    safe=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    title='Blind event-grouped labeling rehearsal' if blind else 'ORBIT consolidated review'
    notice=('No AI suggestions or previous judgments are embedded. Pilot events have prior development exposure: use new independent humans for rehearsal; final evaluation needs untouched events.' if blind else
            'AI suggestions are unreviewed and are separate from your response fields. Existing judgments are read-only. Reserved evaluation-event labels are withheld. This page does not change public scores.')
    style='body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;background:#f6f7f9;color:#17202a}article{background:white;border:1px solid #ccd2d9;padding:1.2rem;margin:1rem 0;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.5 system-ui}summary{cursor:pointer}label{display:block;margin:.6rem 0}input,select,textarea{font:inherit;padding:.35rem}textarea{width:95%}.flag{color:#8a3300}.draft{background:#fff4cc;padding:.7rem}button{font:inherit;padding:.5rem;margin:.3rem}small{overflow-wrap:anywhere}'
    parts=[f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title><style>{style}</style><h1>{title}</h1><p>{notice}</p>',
           '<p>Labels: support, oppose, no_stance, mixed, unresolved. Use not_applicable only for date exclusions. Partial Ukraine-specific evidence is not automatically the full territorial target. Keep source and text holds separate from stance.</p>',
           '<label>Filter text <input id="search" aria-label="Filter review items"></label><button id="save">Export responses as CSV</button><p id="count"></p><main>']
    esc=lambda s:html.escape(str(s),quote=True)
    for n,row in enumerate(rows):
        parts.append(f'<article data-index="{n}" id="{esc(row["row_id"])}"><h2>{esc(row["row_id"])} · {esc(row["actor_id"])} · {esc(row["event_date"])}</h2>')
        parts.append(f'<p><b>Proposition:</b> {esc(row["lens_proposition"])}</p><p>Selection: {esc(row["selection_kind"])} · Event: {esc(row["event_id"])}</p>')
        parts.append(f'<p class="flag">{esc(row.get("quality_flags", ""))}</p><p>{esc(row["source_qualification"])}</p>')
        parts.append(f'<small>Candidate {esc(row["candidate_id"])} · offsets [{row["start"]}, {row["end"]}) · language {esc(row["language"])} · <a href="{esc(row["source_url"])}">Official source</a></small>')
        parts.append(f'<details><summary>Context before</summary><pre>{esc(row["context_before"])}</pre></details><h3>Exact stored passage</h3><pre>{esc(row["exact_passage"])}</pre>')
        parts.append(f'<details><summary>Aligned reading aid (line joining only; exact source above)</summary><pre>{esc(row["reading_text"])}</pre></details>')
        parts.append(f'<details><summary>Context after</summary><pre>{esc(row["context_after"])}</pre></details>')
        if not blind:
            parts.append(f'<p>Review priority: {esc(row["priority_reasons"])} · Role: {esc(row["event_role"])}</p>')
            if row['existing_label']:parts.append(f'<p><b>Recorded judgment:</b> {esc(row["existing_label"])} · {esc(row["existing_provenance"])}</p><p>{esc(row["existing_review_notes"])}</p>')
            if row['ai_suggested_label']:parts.append(f'<div class="draft"><b>AI-generated, unreviewed suggestion:</b> {esc(row["ai_suggested_label"])}<p>{esc(row["ai_rationale"])}</p></div>')
            if row['event_role']=='evaluation_rehearsal':parts.append('<p>Reserved event. Label only in the separate blind export; AI and prior labels are withheld here.</p>')
        if blind or row.get('event_role')!='evaluation_rehearsal':
            options=''.join(f'<option value="{v}">{v or "Leave blank"}</option>' for v in ('','support','oppose','no_stance','mixed','unresolved','not_applicable'))
            parts.append(f'<label>Your label <select data-field="human_label">{options}</select></label><label>Annotator ID <input data-field="human_annotator_id"></label><label>Review notes / deferral reason <textarea data-field="human_review_notes"></textarea></label>')
            parts.append('<details><summary>Separate source, text, attribution and scope review</summary>')
            for field,values in QUALITY_RESPONSE_OPTIONS.items():
                options=''.join(f'<option value="{value}">{value or "Leave blank"}</option>' for value in ('',)+values)
                parts.append(f'<label>{esc(field.replace("human_", "").replace("_", " "))}<select data-field="{field}">{options}</select></label>')
            parts.append('</details>')
            if blind:parts.append('<label>Independent judgment: confirm no AI suggestions or prior labels were seen <input type="checkbox" data-field="human_independent"></label>')
            else:parts.append('<p>Review of this page is assisted and non-independent. It does not create an independent human vote.</p>')
        parts.append('</article>')
    parts.append('</main><p>Export before closing. Responses stay in this page until you download the CSV; no remote submission or automatic saving occurs.</p>')
    # No server, third-party script, inline raw source HTML, or network submission.
    parts.append('<script id="review-data" type="application/json">'+safe+'</script>')
    parts.append('''<script>
const rows=JSON.parse(document.getElementById('review-data').textContent);
const articles=[...document.querySelectorAll('article')];
document.getElementById('count').textContent=rows.length+' items';
document.getElementById('search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();articles.forEach(a=>a.hidden=!a.textContent.toLowerCase().includes(q));});
document.getElementById('save').addEventListener('click',()=>{
const exported=rows.map(r=>({...r}));
articles.forEach(a=>{a.querySelectorAll('[data-field]').forEach(el=>{exported[Number(a.dataset.index)][el.dataset.field]=el.type==='checkbox'?String(el.checked):el.value;});});
const fields=Object.keys(exported[0]);const quote=v=>('"'+String(v??'').replaceAll('"','""')+'"');
const csv='\\ufeff'+[fields.map(quote).join(','),...exported.map(r=>fields.map(f=>quote(r[f])).join(','))].join('\\r\\n');
const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='orbit-review-return.csv';a.click();URL.revokeObjectURL(url);
});
</script></html>''')
    save_text_immutable(path,''.join(parts))


def build_workflow():
    from .aggregation import aggregate
    from .training import prepare_training
    records,candidates,index,texts,segments,annotations,rows,screenings,clean,sha=corpus_snapshot()
    output=ROOT.parent/'.local/workflow-v1'
    draft_path=output/'sealed/draft_pass.json'
    draft=json.loads(draft_path.read_text())
    if draft['input_snapshot_sha256']!=sha or set(draft['decisions'])!={key(c) for c in clean}:
        raise ValueError('Draft map does not cover exactly the frozen clean unreviewed snapshot')
    controls={c['id'] for c in candidates if c['id'].startswith('claim-control-v2-')}
    split=evaluation_design(candidates,index,controls)
    write_immutable(ROOT/'workflow/v1/event_split.json',split)
    held=set(split['reserved_event_ids'])
    suggestions=[]
    for candidate in clean:
        decision=draft['decisions'][key(candidate)]
        if decision['label'] not in ('support','oppose','no_stance','mixed','unresolved'):raise ValueError('Invalid AI draft label')
        row=rows[candidate['id']]
        suggestions.append(dict(suggestion_version='1.0.0',record_type='ai_suggestion',
            id='suggestion-'+digest(f"{candidate['id']}:{digest(draft_path.read_bytes())}".encode()),
            candidate_id=candidate['id'],event_id=candidate['event_id'],label=decision['label'],rationale=decision['rationale'],
            review_flags=decision['review_flags'],origin='ai_generated',review_status='unreviewed',annotator_id=None,independent_human=False,
            model_probability=None,calibrated=False,scoring_eligible=False,training_approved=False,
            method='single_assistant_contextual_pass_frozen_decision_map',input_snapshot_sha256=sha,
            evidence_context_sha256=digest((row['context_before']+row['exact_passage']+row['context_after']).encode()),
            evaluation_sealed=candidate['event_id'] in held))
    write_immutable(output/'sealed/all_suggestions.json',suggestions)
    for suggestion in suggestions:
        SUGGESTION_VALIDATOR.validate(suggestion)
    write_immutable(output/'development_suggestions.json',[s for s in suggestions if not s['evaluation_sealed']])
    suggestion_index={s['candidate_id']:s for s in suggestions}
    review_rows=[];ledger=[]
    for candidate in candidates:
        identifier=candidate['id'];row=rows[identifier];screening=screenings[identifier]
        existing=annotations.get(identifier);suggestion=suggestion_index.get(identifier)
        reserved=candidate['event_id'] in held
        rank,reasons=priority(screening,None if reserved else suggestion,None if reserved else existing)
        doc=index[candidate['document_id']]
        export={**row,'reading_text':candidate['reading_text'],'source_qualification':doc['translation_provenance'] or 'Source/delivery qualifications remain in source review; no scoring clearance.',
            'quality_flags':';'.join(screening['effective_flags']),'quarantine':str(screening['quarantine']).lower(),
            'mechanical_resolutions':';'.join(screening['mechanical_resolutions']),
            'event_role':'evaluation_rehearsal' if reserved else 'development_only','priority':rank,'priority_reasons':reasons,
            'existing_annotation_id':existing['id'] if existing and not reserved else '',
            'existing_label':existing['label'] if existing and not reserved else '',
            'existing_provenance':existing['review_provenance'] if existing and not reserved else '',
            'existing_review_notes':existing['review_notes'] if existing and not reserved else '',
            'ai_suggested_label':suggestion['label'] if suggestion and not reserved else '',
            'ai_rationale':suggestion['rationale'] if suggestion and not reserved else '',
            'ai_review_flags':';'.join(suggestion['review_flags']) if suggestion and not reserved else '',
            'human_label':'','human_annotator_id':'','human_review_notes':'','human_independent':'false'}
        export.update({field:'' for field in QUALITY_RESPONSE_OPTIONS})
        # Old task human fields are always blank in this new export, never history copies.
        review_rows.append(export)
        ledger.append(dict(candidate_id=identifier,document_id=candidate['document_id'],event_id=candidate['event_id'],
            actor_id=doc['actor_id'],lens_id=candidate['lens_id'],text_sha256=candidate['text_sha256'],start=candidate['start'],end=candidate['end'],
            source_url=doc['canonical_url'],selection_kind=row['selection_kind'],original_flags=screening['original_flags'],effective_flags=screening['effective_flags'],
            quarantine=screening['quarantine'],exclusion_reasons=screening['quarantine_reasons']+['no_validated_calibrated_model_output'],
            existing_annotation_id=existing['id'] if existing else None,ai_suggestion_id=suggestion['id'] if suggestion else None,
            event_role=split['event_roles'][candidate['event_id']],score=None,weight=None,contribution=None))
    review_rows.sort(key=lambda r:(-r['priority'],r['actor_id'],r['event_date'],r['start'],r['lens_id']))
    write_immutable(output/'review_queue.json',review_rows)
    write_csv(output/'review_queue.csv',review_rows)
    render_html(output/'review.html',review_rows)
    blind=[]
    for identifier in split['blind_candidate_ids']:
        row=next(r for r in review_rows if r['candidate_id']==identifier)
        # Allowlist only evidence, source qualifiers, source quality and blank responses.
        keep=['row_id','candidate_id','document_id','event_id','actor_id','event_date','lens_id','lens_proposition',
              'selection_kind','source_url','attachment_url','language','text_sha256','start','end','exact_passage',
              'context_start','context_end','context_before','context_after','reading_text','source_qualification',
              'human_label','human_annotator_id','human_review_notes','human_independent']+list(QUALITY_RESPONSE_OPTIONS)
        blind.append({k:row[k] for k in keep})
    write_immutable(output/'blind_evaluation.json',blind)
    write_csv(output/'blind_evaluation.csv',blind)
    render_html(output/'blind_evaluation.html',blind,blind=True)
    write_immutable(output/'quality_screen.json',list(screenings.values()))
    write_immutable(output/'quarantine.json',[s for s in screenings.values() if s['quarantine']])
    write_immutable(output/'evidence_ledger.json',ledger)
    # Collection and scoring coverage remain separate. All five actors/lenses are explicit.
    coverage=[]
    from .validation import load_config
    actors,lenses=load_config()
    for actor in actors:
        for lens in lenses:
            subset=[c for c in candidates if index[c['document_id']]['actor_id']==actor and c['lens_id']==lens]
            events=sorted({c['event_id'] for c in subset})
            actor_events=sorted({r['event_id'] for r in records if r['record_type']=='document' and r['actor_id']==actor})
            applicable=[e for e in actor_events if index[e]['event_date']>=lenses[lens]['applicable_from']
                        and (not lenses[lens]['applicable_until'] or index[e]['event_date']<=lenses[lens]['applicable_until'])]
            coverage.append(dict(actor_id=actor,lens_id=lens,collected_events=len(actor_events),
                temporally_applicable_collected_events=len(applicable),retrieved_candidate_events=len(events),
                candidate_records=len(subset),clean_records=sum(not screenings[c['id']]['quarantine'] for c in subset),
                quarantined_records=sum(screenings[c['id']]['quarantine'] for c in subset),
                reviewed_records=sum(c['id'] in annotations for c in subset),
                ai_draft_records=sum(c['id'] in suggestion_index for c in subset),eligible_scored_events=0,score=None,
                event_counts_by_year_quarter=dict(Counter(index[e]['event_date'][:4]+'-Q'+str((int(index[e]['event_date'][5:7])-1)//3+1) for e in events)),
                annual_coverage_gate='failed_no_eligible_scored_events',missing_is_not_neutral=True))
    write_immutable(output/'coverage.json',coverage)
    training_rows=[dict(a,event_id=index[a['claim_id']]['event_id']) for a in records if a['record_type']=='annotation']
    preflight=prepare_training(training_rows,split)
    write_immutable(output/'training_preflight.json',preflight)
    # A separate, conspicuously synthetic worked example exercises the engine.
    fixture_rows=[]
    for q in range(1,5):
        for day in (1,2):
            fixture_rows.append(dict(origin='test_fixture',claim_id=f'SYNTHETIC-Q{q}-E{day}-C1',canonical_claim_key='SYNTHETIC-claim',
                event_id=f'SYNTHETIC-Q{q}-E{day}',actor_id='SYNTHETIC_ACTOR',lens_id='SYNTHETIC_LENS',
                event_date=f'2024-{3*q-2:02}-{day:02}',stream='SYNTHETIC_TEST_ONLY',support_probability=.75 if q<=2 else .25))
    fixture=aggregate(fixture_rows,'SYNTHETIC_ACTOR','SYNTHETIC_LENS',2024,'SYNTHETIC_TEST_ONLY',allow_fixtures=True)
    write_immutable(output/'SYNTHETIC_aggregation_fixture.json',fixture)
    report=dict(workflow_version=POLICY['workflow_version'],input_snapshot_sha256=sha,candidates=len(candidates),
        unchanged_retrieved_candidates=len(candidates)-len(controls),preserved_random_controls=len(controls),
        quarantined=sum(s['quarantine'] for s in screenings.values()),clean=sum(not s['quarantine'] for s in screenings.values()),
        clean_pending=len(clean),ai_suggestions=len(suggestions),ai_label_counts=dict(Counter(s['label'] for s in suggestions)),
        development_visible_ai_suggestions=sum(not s['evaluation_sealed'] for s in suggestions),
        evaluation_sealed_ai_suggestions=sum(s['evaluation_sealed'] for s in suggestions),
        mechanically_resolved_headers=sum(bool(s['mechanical_resolutions']) for s in screenings.values()),
        quarantine_reason_counts=dict(Counter(f for s in screenings.values() for f in s['quarantine_reasons'])),
        existing_historical_judgments=sum(r['record_type']=='annotation' for r in records),independent_judgments=0,
        blind_events=len(held),blind_items=len(blind),real_scores_computed=0,training_executed=False,
        caveats=['Suggestions are frozen assistant drafts, not trained classifier outputs or human annotations.',
                 'Pilot exposure prevents confirmatory evaluation claims; selected rehearsal events are excluded from all training/tuning.',
                 'Current source coverage cannot meet annual coverage gates; public design and scores remain unchanged.'])
    write_immutable(output/'report.json',report)
    write_immutable(ROOT/'workflow/v1/report.json',report)
    write_immutable(ROOT/'workflow/v1/pass_manifest.json',dict(pass_version=draft['pass_version'],
        private_pass_path='.local/workflow-v1/sealed/draft_pass.json',pass_sha256=digest(draft_path.read_bytes()),
        prompt_sha256=digest(draft['prompt'].encode()),input_snapshot_sha256=sha,
        suggestion_count=len(suggestions),reproduction='Replay frozen private map over exact snapshot; no new model call or training. Keep this map in the permitted private backup with cached source artifacts.'))
    write_immutable(output/'manifest.json',dict(workflow_version=POLICY['workflow_version'],
        artifacts={str(p.relative_to(output)):digest(p.read_bytes()) for p in output.rglob('*') if p.is_file() and p.name!='manifest.json'},
        private_only=True,retention='Attached workspace retention observed; fresh-machine persistence is not guaranteed. Preserve a permitted private copy, never public source redistribution.'))
    return report


if __name__=='__main__':
    print(json.dumps(build_workflow(),indent=2))
