"""Experimental component evidence; never migrates strict labels or W1.

Directions are assistant-authored rule suggestions, not human checks or model
predictions. Scope shortcomings are separate from source/extraction defects.
"""
import argparse,csv,json,re
from collections import Counter
from pathlib import Path
from .focal_retrieval import OUT,OLD
from .focal_review import PACKET as STRICT,LENSES,scope_complete,write_table,reading_map
from .validation import ROOT,digest
from .collect import write_json,utcnow
from .development_review import render
from .workflow import QUALITY_RESPONSE_OPTIONS

VERSION='experimental-components-proposal-1.0.0'
PACKET=ROOT.parent/'.local/development-components-focal-v2'
SCOPE_HOLDS={'partial_territorial_scope','W1_scope_not_established','W1_legal_territorial_extent_review','W1_territorial_exception_or_preinvasion_line'}
COMPONENT_TARGETS={
 'territorial_recognition':'Ukraine has sovereignty / territorial integrity over the Ukrainian territory addressed by this passage.',
 'troop_withdrawal':'Russian forces should withdraw from the Ukrainian territory addressed by this passage.',
 'military_assistance':'External military assistance to Ukraine should be provided / continued; preserve measure-specific limits.',
 'sanctions':'Russia-related sanctions over Ukraine should be imposed / maintained; preserve measure-specific limits.',
 'invasion_responsibility':'Russia bears responsibility for initiating the February 2022 full-scale invasion.'}

def interpret(r):
    p=r['exact_passage'];local=r['context_before']+' '+p+' '+r['context_after'];lens=r['lens_id']
    direction='unresolved';expression='explicit';basis=p
    if lens=='territorial_recognition':
        positive=re.search(r'\b(?:support|reaffirm|reiterate|respect|uphold|commit|defend|recognis|recogniz)[\w\s,\-’\']{0,150}(?:territorial integrity|sovereignty|independen)|(?:territorial integrity|sovereignty)[^.!?]{0,100}(?:Ukraine|Ukrainian)',p,re.I|re.S)
        refusal=re.search(r'(?:not|never|cannot|reject|illegal|unlawful|non-recognition)[^.!?]{0,120}(?:annex|recogni)|(?:annex)[^.!?]{0,100}(?:illegal|not|never|unlawful)',p,re.I|re.S)
        if positive:
            direction='support';basis=positive.group()
            if re.search(r'\bnot\s*$',p[max(0,positive.start()-15):positive.start()],re.I):direction='unresolved'
        elif refusal and re.search(r'Ukraine|Ukrainian|Crimea|Sevastopol|Donetsk|Luhansk|Kherson|Zaporiz',local,re.I):direction='support';expression='contextually_implied';basis=refusal.group()
        if re.search(r'\b(?:we|our government)\b[^.!?]{0,60}(?:recognise|recognize)[^.!?]{0,90}(?:part of Russia|Russian sovereignty)',p,re.I|re.S):direction='oppose'
        if re.search(r'\b(?:do not support|do not recogni[sz]e|deny)\s+(?:Ukraine[’\']s|Ukrainian)\s+(?:sovereignty|territorial integrity)',p,re.I):direction='oppose'
    elif lens=='troop_withdrawal':
        if re.search(r'withdraw|withdrawal|leave',p,re.I):
            direction='support' if re.search(r'call|demand|must|should|urge|request|need|insist|reaffirm',p,re.I) else 'unresolved'
        if re.search(r'\b(?:reject|oppose)\b[^.!?]{0,70}\bwithdraw',p,re.I):direction='oppose'
    else:
        from .focal_review import proposal
        direction,_=proposal(r)
        if lens=='military_assistance' and re.search(r'equip[^.!?]{0,40}Ukraine[^.!?]{0,40}defend',p,re.I):expression='contextually_implied'
    if lens=='territorial_recognition' and direction=='support' and not re.search(r'Ukraine|Ukrainian|Crimea|Sevastopol|Donetsk|Luhansk|Kherson|Zaporiz',p,re.I):expression='contextually_implied'
    scope='comprehensive' if scope_complete(p) else ('specified_or_limited' if re.search(r'Crimea|Sevastopol|Donetsk|Luhansk|Kherson|Zaporiz|Donbas|pre.?24|pre.?February|specific|particular',p,re.I) else 'unspecified')
    annexation='not_addressed';annexation_object=''
    if re.search('annex',p,re.I):
        annexation='non_recognition' if re.search(r'illegal|unlawful|never recogni|not recogni|non.recognition|reject|cannot (?:be|and)',p,re.I) else 'unresolved'
        annexation_object=';'.join(sorted(set(re.findall(r'Crimea|Sevastopol|Donetsk|Luhansk|Kherson|Zaporizhzhia',p,re.I)))) or 'annexations referenced in exact text; extent requires review'
    elif re.search(r'recogni[^.!?]{0,90}(?:Donetsk|Luhansk|separatist)',p,re.I):annexation='separatist_entity_recognition_distinct_from_annexation'
    conditions=p if re.search(r'\bif\b|unless|until|provided that|conditional|condition|subject to|as long as|negotiat|ceasefire|phased|immediate|unconditional|without delay|use of|restric',p,re.I) else ''
    return dict(direction=direction,expression=expression,scope=scope,annexation=annexation,annexation_object=annexation_object,conditions=conditions,basis=basis,basis_start=r['start']+p.index(basis),basis_end=r['start']+p.index(basis)+len(basis),reason='Exact passage '+('expresses' if expression=='explicit' else 'contextually implies')+' '+direction+' for this component only. '+('Comprehensive territorial extent is explicit.' if scope=='comprehensive' else 'Territorial / measure extent remains '+scope+'.')+' Missing dimensions do not change the existing strict target. Negation and qualifications remain in the original passage.')

def component_candidates():
    held=json.loads((OUT/'held.json').read_text());out=[]
    for r in held:
        if not r['quality_flags'] or not set(r['quality_flags'])<=SCOPE_HOLDS:continue
        if r['actor_id'] not in ['USA','EU','TUR','IND','ZAF']:continue
        if r['event_role']!='development_only':raise ValueError('Reserved component evidence')
        if r['lens_id'] not in ['territorial_recognition','troop_withdrawal']:continue
        local=r['exact_passage']+' '+r['context_before'][-500:]+' '+r['context_after'][:350]
        if not re.search(r'Ukraine|Ukrainian|Crimea|Sevastopol|Donetsk|Luhansk|Kherson|Zaporiz',local,re.I):continue
        if not re.search(r'[.!?][”"\')\]]?\s*$',r['exact_passage'].strip()):continue
        out.append(r)
    return out

def build():
    from .focal_review import build as strict_build
    if not (STRICT/'review_queue.json').exists():strict_build()
    templates=json.loads((STRICT/'review_queue.json').read_text());template=templates[0];rows=[];refs={};suggestions=[]
    for r in component_candidates():
        cid='component-focus2-'+digest((VERSION+':'+r['candidate_id']).encode());v=dict(r,candidate_id=cid,derived_from_candidate_id=r['candidate_id'],component_protocol=VERSION,strict_target_eligible=False,technical_quality_flags=[],target_scope_flags=r['quality_flags'])
        suggestion=interpret(r);v['experimental_components']=suggestion
        row={k:'' for k in template};row.update({k:template[k] for k in ['queue_version','record_type','actor_role','offset_unit','codebook_version','human_independent']})
        row.update(queue_version=VERSION,row_id='C2-'+digest(cid.encode())[:12],candidate_id=cid,selection_kind=r['acquisition_kind'],passage_id='passage-'+digest(f"{r['document_id']}:{r['start']}:{r['end']}".encode()),event_id=r['event_id'],document_id=r['document_id'],actor_id=r['actor_id'],event_date=r['event_date'],lens_id=r['lens_id'],lens_proposition=LENSES[r['lens_id']]['definition'],source_url=r['source_url'],document_issuer=r['issuer'],speaker=r['speaker'],language=r['language'],language_review_required='false',text_sha256=r['text_sha256'],start=str(r['start']),end=str(r['end']),exact_passage=r['exact_passage'],context_start=str(r['start']-len(r['context_before'])),context_end=str(r['end']+len(r['context_after'])),context_before=r['context_before'],context_after=r['context_after'],reading_text=r['reading_text'],source_qualification=r['translation_provenance']+'; source-cleared component evidence; strict scope hold preserved; targeted training acquisition, not representative position estimation',quality_flags=';'.join(r['quality_flags']),quarantine='false',mechanical_resolutions=';'.join(r.get('previous_quality_flags',[])),event_role='development_only',leakage_group_id=r['leakage_group_id'],revises_candidate_id=r.get('revises_candidate_id',''),recovery_of=r.get('recovery_of',''),attribution_evidence=r.get('attribution_evidence',''),shared_endorsing_actor_ids=';'.join(r.get('shared_endorsing_actor_ids',[])),priority=80 if suggestion['direction']=='unresolved' else 50,priority_reasons='component_scope_not_full_strict_target',ai_suggested_label=suggestion['direction'],ai_rationale=suggestion['reason'],ai_review_flags='Experimental COMPONENT direction only; assistant-authored contextual rules; AI-generated, unreviewed; no Badr_A checking / training approval',review_target='experimental_component_direction',component_protocol=VERSION,component_proposition=COMPONENT_TARGETS[r['lens_id']],component_expression=suggestion['expression'],component_scope=suggestion['scope'],component_annexation=suggestion['annexation'],component_annexation_object=suggestion['annexation_object'],component_conditions=suggestion['conditions'],component_basis=suggestion['basis'],strict_target_status='NOT eligible for full target; original scope hold and strict judgments unchanged',derived_from_candidate_id=r['candidate_id'])
        rows.append(row);refs[cid]=v;suggestions.append(dict(candidate_id=cid,original_candidate_id=r['candidate_id'],origin='ai_generated_unreviewed',human_reviewed=False,training_approved=False,**suggestion))
    rows.sort(key=lambda r:(['IND','TUR','ZAF','EU','USA'].index(r['actor_id']),r['event_date'],r['row_id']))
    packet=digest(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode());PACKET.mkdir(exist_ok=True);old=json.loads((PACKET/'manifest.json').read_text()) if (PACKET/'manifest.json').exists() else {}
    if list((ROOT.parent/'.local/component-returns').glob('*/ledger.json')) and old.get('packet_id')!=packet:raise ValueError('Returned component packet frozen; increment version')
    created=old.get('created_at',utcnow()) if old.get('packet_id')==packet else utcnow()
    write_json(PACKET/'review_queue.json',rows);write_table(PACKET/'orbit-development-review.csv',rows)
    p=PACKET/'orbit-development-review.html'
    if p.exists():p.unlink()
    render(p,rows,packet,component_mode=True);write_json(PACKET/'source_refs.json',refs);write_json(PACKET/'ai_suggestions.json',suggestions)
    write_json(PACKET/'progress-backup.json',dict(format='orbit-development-responses-v2',packet_id=packet,saved_at=created,provenance='Experimental AI-generated, unreviewed component suggestions',settings={},responses={}))
    write_json(PACKET/'manifest.json',dict(version=VERSION,packet_id=packet,created_at=created,records=len(rows),new_clean_records=len(rows),mechanically_clean=len(rows),quarantined=0,evaluation_records=0,events=sorted({r['event_id'] for r in rows}),files={n:digest((PACKET/n).read_bytes()) for n in ['review_queue.json','orbit-development-review.csv','orbit-development-review.html','source_refs.json','ai_suggestions.json','progress-backup.json']}))
    report=dict(version=VERSION,records=len(rows),events=len({r['event_id'] for r in rows}),groups=len({r['leakage_group_id'] for r in rows}),new_pairs=sum(r['selection_kind']=='newly_collected' for r in rows),recovered_pairs=sum(r['selection_kind']=='recovered_held' for r in rows),by_actor=dict(Counter(r['actor_id'] for r in rows)),by_lens=dict(Counter(r['lens_id'] for r in rows)),suggested_component_directions=dict(Counter(r['direction'] for r in suggestions)),strict_target_eligible=0,new_approved=0)
    write_json(OUT/'component_yield.json',report);print(json.dumps(report,indent=2));return report

def import_component_return(path,review_id):
    from .review_import import audit_return,validate_return
    from .reviewed import write_immutable
    if not re.fullmatch(r'[A-Za-z0-9_-]+',review_id):raise ValueError('Unsafe review ID')
    with Path(path).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    baseline=json.loads((PACKET/'review_queue.json').read_text());manifest=json.loads((PACKET/'manifest.json').read_text())
    for n,h in manifest['files'].items():
        if digest((PACKET/n).read_bytes())!=h:raise ValueError('Frozen component packet changed')
    audit=audit_return(rows,baseline)
    if audit['fatal_conflicts']:raise ValueError(json.dumps(audit))
    reviewed=validate_return(rows,baseline);refs=json.loads((PACKET/'source_refs.json').read_text())
    for r in refs.values():
        t=Path(r['source_text_path']).read_text()
        if r['event_role']!='development_only' or r['technical_quality_flags'] or digest(t.encode())!=r['text_sha256'] or t[r['start']:r['end']]!=r['exact_passage']:raise ValueError('Component source/reference gate failed')
    folder=ROOT.parent/'.local/component-returns'/review_id;sha=digest(Path(path).read_bytes())
    if (folder/'ledger.json').exists():
        ledger=json.loads((folder/'ledger.json').read_text())
        if ledger['submission_sha256']!=sha:raise ValueError('Cannot overwrite previous component review')
        return ledger
    records=[dict(record_type='experimental_component_review',id='component-review-'+digest((review_id+':'+r['candidate_id']+sha).encode()),candidate_id=r['candidate_id'],derived_from_candidate_id=r['derived_from_candidate_id'],component_protocol=VERSION,direction=r['human_label'] or None,review_notes=r['human_review_notes'],annotator_id=r['human_annotator_id'],origin='ai_assisted_reviewed',blind_independent_annotation=False,training_approved=False,strict_target_label_changed=False,source_scope_holds_preserved=True,quality_responses={field:r.get(field,'') for field in QUALITY_RESPONSE_OPTIONS},component_suggestion=refs[r['candidate_id']]['experimental_components']) for r in reviewed]
    write_immutable(folder/'reviews.json',records);write_immutable(folder/'validation_audit.json',audit)
    ledger=dict(version=VERSION,submission_sha256=sha,baseline_sha256=manifest['files']['review_queue.json'],reviewed=len(records),strict_annotations_created=0,training_approvals_created=0)
    write_immutable(folder/'ledger.json',ledger);return ledger

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--import-csv',type=Path);p.add_argument('--review-id');a=p.parse_args()
    if a.import_csv:
        if not a.review_id:p.error('--review-id required')
        print(json.dumps(import_component_return(a.import_csv,a.review_id)))
    else:build()
