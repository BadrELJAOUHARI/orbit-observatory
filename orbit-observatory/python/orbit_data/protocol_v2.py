"""Adopted component protocol and consolidated append-only development returns."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from collections import Counter,defaultdict
from .validation import ROOT,digest
from .collect import write_json
from .workflow import write_csv
OUT=ROOT.parent/'.local/consolidated-protocol-v2'
PACKETS=['development-review-sprint-v1','development-review-focal-v2','development-components-focal-v2']
DIRECTIONS=['support','oppose','mixed','no_stance','unresolved']
CHOICES={'strict_label':DIRECTIONS+['not_applicable'],'integrity_direction':DIRECTIONS,'annexation_direction':['non_recognition','recognition','mixed','no_stance','unresolved'],'direction':DIRECTIONS,'measure_direction':DIRECTIONS,'expression':['explicit','contextually_implied'],'extent':['comprehensive','specified_or_limited','unspecified','unresolved'],'source_quality':['eligible','ineligible','needs_review'],'attribution_quality':['attributable','wrong_actor','needs_review'],'text_quality':['usable','defective','needs_review'],'language_quality':['usable','needs_review']}
FREE=['prior_response_json','conditions','scope_details','annexation_object','timing','measure','overall_vs_measure','basis','annotator_id','review_notes']
FIELDS=list(CHOICES)+FREE
SCOPE_HOLDS={'partial_territorial_scope','W1_scope_not_established','W1_legal_territorial_extent_review','W1_territorial_exception_or_preinvasion_line'}

def targets(row):
 common=['prior_response_json','expression','extent','scope_details','conditions','basis','source_quality','attribution_quality','text_quality','language_quality','annotator_id','review_notes']
 lens=row['lens_id'];axes=['integrity_direction','annexation_direction','annexation_object'] if lens=='territorial_recognition' else ['direction']
 if lens=='troop_withdrawal':axes+=['timing']
 if lens in ('military_assistance','sanctions'):axes+=['measure_direction','measure','overall_vs_measure']
 return ([] if row['task_kind']=='component' else ['strict_label'])+axes+common

def build():
 rows=[];seen=set();refs={};packets={}
 for name in PACKETS:
  p=ROOT.parent/'.local'/name;m=json.loads((p/'manifest.json').read_text());base=json.loads((p/'review_queue.json').read_text());packets[m['packet_id']]=dict(name=name,baseline=base)
  for n,h in m['files'].items():assert digest((p/n).read_bytes())==h
  for row in base:
   assert row['event_role']=='development_only'
   kind='component' if name==PACKETS[-1] else 'strict';key=(row['candidate_id'],kind)
   if key in seen:continue
   seen.add(key);r=dict(row,task_kind=kind,original_packet_id=m['packet_id'],protocol_version='components-v2.0.0',allowed_response_fields=[])
   r['allowed_response_fields']=targets(r);r['response']={f:'' for f in FIELDS};rows.append(r)
  refs.update(json.loads((p/'source_refs.json').read_text()))
 groups=defaultdict(list)
 for r in rows:groups[(r['document_id'],str(r['start']),str(r['end']))].append(r['candidate_id'])
 for r in rows:
  ref=refs[r['candidate_id']];r['display_issuer']=r.get('document_issuer') or ref.get('issuer') or 'Not listed; verify official source';r['display_speaker']=r.get('speaker') or ref.get('speaker') or 'Not listed; verify attribution in context'
  r['shared_passage_tasks']=groups[(r['document_id'],str(r['start']),str(r['end']))]
  r['overlapping_task_ids']=[x['candidate_id'] for x in rows if x['candidate_id']!=r['candidate_id'] and x['document_id']==r['document_id'] and int(x['start'])<int(r['end']) and int(r['start'])<int(x['end'])]
 keys=sorted({k for r in rows for k in r});rows=[{k:r.get(k,'') for k in keys} for r in rows]
 OUT.mkdir(exist_ok=True);packet=digest(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode())
 if (OUT/'manifest.json').exists() and list((ROOT.parent/'.local/consolidated-component-returns').glob('*/records.json')) and json.loads((OUT/'manifest.json').read_text())['packet_id']!=packet:raise ValueError('Reviewed baseline frozen; increment protocol/packet version')
 write_json(OUT/'rows.json',rows);write_json(OUT/'source_refs.json',refs);write_json(OUT/'legacy_packets.json',packets)
 flat=[{**{k:v for k,v in r.items() if k!='response'},**{'human_'+f:'' for f in FIELDS}} for r in rows]
 # JSON values are immutable strings in CSV.
 csvrows=[{k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in flat]
 p=OUT/'review.csv'
 if p.exists():p.unlink()
 write_csv(p,csvrows);write_json(OUT/'csv_baseline.json',csvrows)
 report=dict(protocol='components-v2.0.0',packet_id=packet,tasks=len(rows),strict_tasks=sum(r['task_kind']=='strict' for r in rows),component_tasks=sum(r['task_kind']=='component' for r in rows),unique_passages=len(groups),events=len({r['event_id'] for r in rows}),groups=len({r['leakage_group_id'] for r in rows}),existing_reviewed=sum(bool(r.get('existing_annotation_id')) for r in rows),server_saved_responses=0,evaluation_tasks=0)
 report['primary_output_inventory']={'legacy_full_target':sum(r['task_kind']=='strict' for r in rows),'new_integrity_direction':sum(r['task_kind']=='component' and r['lens_id']=='territorial_recognition' for r in rows),'new_annexation_recognition':sum(r['task_kind']=='component' and r['lens_id']=='territorial_recognition' for r in rows),'new_withdrawal_direction':sum(r['task_kind']=='component' and r['lens_id']=='troop_withdrawal' for r in rows)}
 report['browser_drafts']='Unknown until imported; never assumed absent'
 write_json(OUT/'manifest.json',report)
 write_json(OUT/'progress-backup.json',dict(format='orbit-components-v2',packet_id=packet,responses={},history={}))
 payload=json.dumps(dict(rows=rows,packet_id=packet,choices=CHOICES,fields=FIELDS,legacy=packets),ensure_ascii=False).replace('<','\\u003c')
 js=(ROOT/'python/orbit_data/ui/protocol_v2.js').read_text()
 (OUT/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>ORBIT consolidated component review</title><style>body{font:16px/1.5 system-ui;max-width:1100px;margin:2rem auto;background:#f4f6f8}section{background:white;padding:1rem;margin:1rem 0}fieldset{margin:1rem 0}pre{white-space:pre-wrap}label{display:block;margin:.5rem}textarea{width:95%}.bar{position:sticky;top:0;background:#f4f6f8;padding:1rem}select,input,button,textarea{font:inherit}</style><h1>ORBIT consolidated development review</h1><p>Protocol components-v2.0.0. Strict labels/W1 remain separate. No suggestions or past labels are automatically approved or migrated. Explicit includes synonyms; implied requires linked-context inference. Specificity is not strength.</p><div class="bar"><select id="actor"><option value="">All actors</option></select><select id="lens"><option value="">All lenses</option></select><select id="year"><option value="">All years</option></select><select id="proposed"><option value="">All prior suggestions</option></select><select id="quality"><option value="all">All quality states</option><option value="clean">Mechanically clean</option><option value="quarantined">Quarantined</option></select><select id="status"><option value="all">All</option><option value="unreviewed">Unreviewed</option></select><label>Annotator ID for edited tasks <input id="annotator-global"></label><button id="json">Export progress JSON</button><button id="csv">Export CSV</button><input id="import" type="file" accept=".json,.csv"><label><input id="replace" type="checkbox">Explicitly allow replacing conflicting responses</label><p id="saved"></p><p id="count"></p></div><main></main><script id="data" type="application/json">'+payload+'</script><script>'+js+'</script>')
 report['files']={n:digest((OUT/n).read_bytes()) for n in ['rows.json','source_refs.json','csv_baseline.json','legacy_packets.json','review.csv','review.html','progress-backup.json']}
 write_json(OUT/'manifest.json',report)
 print(json.dumps({k:v for k,v in report.items() if k!='files'}));return report

def validate(rows):
 manifest=json.loads((OUT/'manifest.json').read_text())
 for name,sha in manifest['files'].items():
  if digest((OUT/name).read_bytes())!=sha:raise ValueError('Frozen baseline changed: '+name)
 baseline=json.loads((OUT/'csv_baseline.json').read_text());expected={r['candidate_id']:r for r in baseline};errors=[];seen=Counter(r.get('candidate_id') for r in rows);answers=[]
 for cid in expected:
  if seen[cid]!=1:errors.append(dict(id=cid,error='missing_or_duplicate'))
 for r in rows:
  cid=r.get('candidate_id');b=expected.get(cid)
  if b is None:errors.append(dict(id=cid,error='unknown'));continue
  if set(r)!=set(b) or any(str(r.get(k,''))!=str(v) for k,v in b.items() if k not in {'human_'+f for f in FIELDS}):errors.append(dict(id=cid,error='immutable_fields_changed'));continue
  response={f:r.get('human_'+f,'') for f in FIELDS};allowed=json.loads(b['allowed_response_fields'])
  for f,value in response.items():
   if value and (f not in allowed or (f in CHOICES and value not in CHOICES[f])):errors.append(dict(id=cid,error='invalid_component',field=f))
  if any(v for k,v in response.items() if k!='prior_response_json'):
   if not response['annotator_id'].strip() or not response['review_notes'].strip():errors.append(dict(id=cid,error='annotator_and_notes_required'))
   answers.append(dict(candidate_id=cid,event_id=b['event_id'],protocol='components-v2.0.0',components=response,strict_codebook='consolidated-v1',withdrawal_rule='W1',origin='ai_assisted_reviewed',blind_independent_annotation=False,training_approved=False,original_passage_unchanged=True))
 if errors:raise ValueError(json.dumps(errors))
 return answers

def eligible(record,component,approval,ref):
 """Record-scoped authorization; absence of unrelated full-target axes is allowed."""
 response=record['components'];value=response.get(component)
 flags=set(ref.get('quality_flags',[]))
 if component!='strict_label':flags-=SCOPE_HOLDS
 approved=component in approval.get(record['candidate_id'],[])
 return bool(approved and value in [v for v in CHOICES.get(component,[]) if v not in ('unresolved','not_applicable','needs_review')] and not flags and ref['event_role']=='development_only' and all(response.get(f) not in ('ineligible','wrong_actor','defective','needs_review') for f in ['source_quality','attribution_quality','text_quality','language_quality']))

def import_return(path):
 with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 records=validate(rows)
 refs=json.loads((OUT/'source_refs.json').read_text())
 for r in records:
  ref=refs[r['candidate_id']];r.update(document_id=ref['document_id'],lens_id=ref['lens_id'],source_text_sha256=ref['text_sha256'],start=ref['start'],end=ref['end']);text=Path(ref['source_text_path']).read_text();assert ref['event_role']=='development_only' and digest(text.encode())==ref['text_sha256'] and text[ref['start']:ref['end']]==ref['exact_passage']
 sha=digest(path.read_bytes());folder=ROOT.parent/'.local/consolidated-component-returns'/sha
 if (folder/'records.json').exists():return dict(imported=len(records),idempotent=True)
 for r in records:r.update(id='component-review-v2-'+digest((sha+':'+r['candidate_id']).encode()),submission_sha256=sha)
 write_json(folder/'records.json',records);(folder/'submission.csv').write_bytes(path.read_bytes());return dict(imported=len(records),idempotent=False)
def export_approved(path):
 approval=json.loads(path.read_text())
 if approval.get('protocol')!='components-v2.0.0' or not approval.get('approved_by') or not isinstance(approval.get('approvals'),dict):raise ValueError('Explicit named record/component authorization required')
 refs=json.loads((OUT/'source_refs.json').read_text());reviewed=defaultdict(list)
 for p in (ROOT.parent/'.local/consolidated-component-returns').glob('*/records.json'):
  for record in json.loads(p.read_text()):reviewed[record['candidate_id']].append(record)
 accepted=[];excluded=[]
 for cid,components in approval['approvals'].items():
  if cid not in refs or not isinstance(components,list):raise ValueError('Invalid authorization record')
  for component in components:
   if component not in ['integrity_direction','annexation_direction','direction','measure_direction','extent','expression','strict_label']:raise ValueError('Invalid authorized component')
   if any(r['components'].get(f) in ('ineligible','wrong_actor','defective','needs_review') for r in reviewed[cid] for f in ['source_quality','attribution_quality','text_quality','language_quality']):excluded.append(dict(candidate_id=cid,component=component,reason='preserved_source_quality_hold'));continue
   candidates=[r for r in reviewed[cid] if r['components'].get(component)]
   values={r['components'][component] for r in candidates}
   if len(values)!=1:excluded.append(dict(candidate_id=cid,component=component,reason='unreviewed_or_conflicting_judgments'));continue
   record=candidates[-1];ref=refs[cid]
   if not eligible(record,component,approval['approvals'],ref):excluded.append(dict(candidate_id=cid,component=component,reason='source_quality_or_unresolved_target'));continue
   text=Path(ref['source_text_path']).read_text()
   if digest(text.encode())!=ref['text_sha256'] or text[ref['start']:ref['end']]!=ref['exact_passage']:raise ValueError('Source integrity changed after review')
   target=(record['components'].get('measure','') if component=='measure_direction' else ('Annexation recognition: '+record['components'].get('annexation_object','unspecified object') if component=='annexation_direction' else component+' for '+ref['lens_id']))
   if component=='measure_direction' and not target:excluded.append(dict(candidate_id=cid,component=component,reason='named_measure_target_missing'));continue
   accepted.append(dict(candidate_id=cid,target_proposition=target,lens_id=ref['lens_id'],actor_role=ref.get('actor_role','auxiliary' if ref['actor_id']=='GBR' else 'focal'),component_target=ref['lens_id']+':'+component,component_field=component,label=record['components'][component],event_id=ref['event_id'],leakage_group_id=ref['leakage_group_id'],actor_id=ref['actor_id'],text=ref['exact_passage'],text_sha256=ref['text_sha256'],start=ref['start'],end=ref['end'],review_metadata={k:record['components'].get(k,'') for k in ['expression','extent','scope_details','conditions','timing','measure','overall_vs_measure','basis','annexation_object']},origin=record['origin'],blind_independent_annotation=False,training_approved=True,authorization_sha256=digest(path.read_bytes()),alignment_score=None))
 target=ROOT.parent/'.local/component-training-freezes'/digest(path.read_bytes());write_json(target/'dataset.json',accepted);write_json(target/'exclusions.json',excluded)
 return dict(included=len(accepted),excluded=len(excluded),path=str(target),models_trained=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--import-csv',type=Path);p.add_argument('--export-approved',type=Path);a=p.parse_args()
 if a.import_csv:print(import_return(a.import_csv))
 elif a.export_approved:print(export_approved(a.export_approved))
 else:build()
