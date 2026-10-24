"""Validate a separate expansion corpus and prepare a development-only return packet.

No model suggestions, human labels, training rows, or public scores are generated.
"""
import json,re,shutil
from collections import Counter,defaultdict
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from .validation import ROOT,digest,load_config
from .reviewed import write_immutable
from .collect import write_json
from .text import normalize
from .annotations import task
from .resegment import source_lines,units
from .development_review import render,RESPONSE_FIELDS
from .workflow import write_csv,csv_cell

OUT=ROOT.parent/'.local/expansion-v6'
PACKET=ROOT.parent/'.local/development-review-expanded-v2-20261023'
ACTORS={'USA','EU','TUR','IND','ZAF','RUS','UKR'}
DOC_SCHEMA={
 'type':'object','required':['document_id','event_id','actor_id','actor_role','event_date','issuer','canonical_url','resolved_url','language','raw_path','raw_sha256','text_path','text_sha256','retrieved_at','quality_issues','event_role'],
 'properties':{**{k:{'type':'string','minLength':1} for k in ['document_id','event_id','issuer','raw_path','text_path']},
 'actor_id':{'enum':sorted(ACTORS)},'actor_role':{'enum':['focal','auxiliary_training_only']},
 'event_role':{'enum':['development_only','evaluation_reserved','auxiliary_development_only']},
 'event_date':{'type':'string','format':'date'},'retrieved_at':{'type':'string','format':'date-time'},
 'canonical_url':{'type':'string','format':'uri'},'resolved_url':{'type':'string','format':'uri'},
 'language':{'enum':['en','fr','ru','und']},'quality_issues':{'type':'array','items':{'type':'string'}},
 'raw_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},'text_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'}}}
DOCUMENT_VALIDATOR=Draft202012Validator(DOC_SCHEMA,format_checker=FormatChecker())

CANDIDATE_SCHEMA={'type':'object','required':['record_type','schema_version','id','document_id','event_id','actor_id','lens_id','text_sha256','start','end','exact_passage','reading_text','source_indices','quality_issues','origin','scoring_eligible','training_approved'],
 'properties':{'record_type':{'const':'expansion_candidate'},'schema_version':{'const':'1.0.0'},
 **{k:{'type':'string','minLength':1} for k in ['id','document_id','event_id','lens_id','exact_passage','reading_text']},
 'actor_id':{'enum':sorted(ACTORS)},'text_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},
 'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},
 'source_indices':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'integer','minimum':0}},
 'quality_issues':{'type':'array','uniqueItems':True,'items':{'type':'string'}},
 'origin':{'const':'retrieval_not_prediction'},'scoring_eligible':{'const':False},'training_approved':{'const':False}}}
CANDIDATE_VALIDATOR=Draft202012Validator(CANDIDATE_SCHEMA)


def event_roles():
    split=json.loads((ROOT/'workflow/expansion-v1/event_split.json').read_text())
    supplement=json.loads((ROOT/'source_manifest/expansion-v1/supplement.json').read_text())
    targeted=json.loads((ROOT/'workflow/expansion-v1/targeted_split-v2.json').read_text())
    roles={**split['event_roles'],**supplement['event_roles'],**targeted['event_roles']}
    effective=OUT/'effective_event_split.json'
    if effective.exists():roles.update(json.loads(effective.read_text())['event_roles'])
    return roles


def clear_catalog(catalog):
    """Exact-copy conflicts attach to the wrongly dated mirror, never the genuine event."""
    docs=[dict(d,quality_issues=list(dict.fromkeys(d['quality_issues']))) for d in catalog]
    by_hash=defaultdict(list)
    for doc in docs:by_hash[(doc['actor_id'],doc['text_sha256'])].append(doc)
    for copies in by_hash.values():
        if len(copies)<2:continue
        # Header year is documentary evidence; do not use the landing URL to choose it.
        text=(OUT/copies[0]['text_path']).read_text();header=text[:1800]
        years={d['year'] for d in copies if str(d['year']) in header}
        genuine=[d for d in copies if d['year'] in years]
        if len(genuine)!=1:
            for d in copies:d['quality_issues'].append('unresolved_duplicate_event_date');d['duplicate_of']=copies[0]['document_id'] if d!=copies[0] else None
        else:
            # A reserved mirror reserves the whole actual communication cluster.
            reserve=any(d['event_role']=='evaluation_reserved' for d in copies)
            source=genuine[0];source['duplicate_of']=None
            if reserve:source['event_role']='evaluation_reserved'
            source['quality_issues']=[x for x in source['quality_issues'] if x!='cross_year_attachment_conflict']
            for d in copies:
                if d is source:continue
                d['duplicate_of']=source['document_id'];d['quality_issues'].append('attachment_header_year_mismatch')
                d['event_role']=source['event_role'] # Mirrored evidence inherits the actual event's split.
    for d in docs:
        d['selection_method']=d.get('selection_method','supplementary_UN_broad_speech')
        d['representative_country_period_sample']=False
        if d['actor_id']=='TUR' and d['year']==2024:
            d['quality_issues'].append('official_press_excerpt_not_full_transcript')
            d['source_type']='official_presidency_speech_report_with_attributed_quotations_UN_mirror'
            d['format_verification_note']='UN attachment reproduces a presidency press report, including President Erdogan said. Treat quotations as excerpts, not a full verbatim transcript.'
        if d['actor_id']=='EU' and d['year']==2014:
            d['language']='fr';d['language_verification_note']='Attachment filename says en, but original body includes French: Monsieur le President. Original retained; language review required.'
        if d['language']=='floor':
            d['language']='en' if d['actor_id']=='EU' and d['year']==2025 else 'und'
            d['language_verification_note']='Floor-language attachment inspected: English body The world faces a crucial choice. OCR still requires visual review.'
        d['quality_issues']=sorted(set(d['quality_issues']))
        d['event_identity_verified']=not any(x in d['quality_issues'] for x in ('attachment_header_year_mismatch','unresolved_duplicate_event_date'))
        # An attachment proves an official prepared communication. Delivery qualification remains.
        d['prepared_statement_qualification']='Check-against-delivery versions are not claimed to be verbatim delivered recordings.'
    return docs


def validate_expansion(docs,claims,roles,root=OUT):
    index={d['document_id']:d for d in docs}
    if len(index)!=len(docs):raise ValueError('Duplicate document ID')
    if len({c['id'] for c in claims})!=len(claims):raise ValueError('Duplicate candidate ID')
    lenses=load_config()[1];seen=set()
    for d in docs:
        DOCUMENT_VALIDATOR.validate(d)
        if d['event_role']!=roles[d['event_id']] and not d.get('duplicate_of'):raise ValueError('Event role changed after reservation')
        for key in ('text','raw'):
            path=(root/d[key+'_path']).resolve()
            if not path.is_relative_to(root.resolve()):raise ValueError('Unsafe source path')
            if digest(path.read_bytes())!=d[key+'_sha256']:raise ValueError('Cached source hash mismatch')
        if (d['actor_role']=='auxiliary_training_only') != (d['actor_id'] in ('RUS','UKR')):raise ValueError('Actor-role mismatch')
    for c in claims:
        CANDIDATE_VALIDATOR.validate(c)
        d=index[c['document_id']];text=(root/d['text_path']).read_text()
        if d['duplicate_of'] or not d['event_identity_verified']:raise ValueError('Uncleared event mirror produced a candidate')
        if c['actor_id']!=d['actor_id'] or c['event_id']!=d['event_id'] or c['text_sha256']!=d['text_sha256']:raise ValueError('Candidate reference mismatch')
        if not 0<=c['start']<c['end']<=len(text) or text[c['start']:c['end']]!=c['exact_passage']:raise ValueError('Exact offsets mismatch')
        indices=c['source_indices']
        if indices!=sorted(set(indices)) or not indices or indices[0]!=c['start'] or indices[-1]!=c['end']-1:raise ValueError('Source index map mismatch')
        if ''.join(' ' if text[i]=='\n' else text[i] for i in indices)!=c['reading_text']:raise ValueError('Reading map mismatch')
        if not lenses[c['lens_id']]['applicable_from']<=d['event_date']:raise ValueError('Temporal scope error')
        key=(c['event_id'],c['lens_id'],c['start'],c['end'])
        if key in seen:raise ValueError('Duplicate event/lens/span')
        seen.add(key)


# Additional Russian retrieval vocabulary only, not a translation, annotation or target change.
RU={'territorial_recognition':['территори','суверен','аннекс','границ'],
    'troop_withdrawal':['вывод','войск','оккупа'],
    'military_assistance':['оруж','военн','вооруж','помощ'],
    'sanctions':['санкц','ограничени'],
    'invasion_responsibility':['агресс','вторжен','операци','напад']}
CONFLICT=re.compile(r'ukrain|ukraïn|украин|ukrayna',re.I)


def retrieve(docs):
    lenses=load_config()[1];claims=[];segments={}
    for d in docs:
        if d.get('duplicate_of') or not d['event_identity_verified']:continue
        text=(OUT/d['text_path']).read_text()
        raw=None if d.get('extraction_history') else (OUT/d['raw_path']).read_bytes()
        physical=source_lines(text,raw)
        us,paras,omitted=units(text,physical)
        segments[d['document_id']]=dict(units=us,omitted=omitted,text_sha256=d['text_sha256'])
        for i,u in enumerate(us):
            if len(u['reading_text'])<45:continue
            # Adjacent sentence context permits explicit anaphora, but is never a label.
            nearby=' '.join(x['reading_text'] for x in us[max(0,i-1):i+2])
            direct_topic=d.get('source_title','').casefold()
            topic_specific=d.get('selection_method')=='targeted_training_acquisition' and 'ukraine conflict' in direct_topic
            if not CONFLICT.search(nearby) and not topic_specific:continue
            for lens in lenses.values():
                if d['event_date']<lens['applicable_from']:continue
                words=RU[lens['id']] if d['language']=='ru' else lens['candidate_keywords_by_language'].get(d['language'],lens['candidate_keywords'])
                if not any(word.casefold() in u['reading_text'].casefold() for word in words):continue
                identifier='claim-exp-'+digest(f"{d['document_id']}:{d['text_sha256']}:{u['start']}:{u['end']}:{lens['id']}".encode())
                issues=list(d['quality_issues'])
                if not re.search(r'[.!?][”’"\)]?$',u['reading_text']):issues.append('incomplete_sentence_boundary')
                if re.search(r'(?i)\b(?:he|she|they) (?:said|stated)|according to|«|[“"]',u['reading_text']):issues.append('quotation_attribution_review')
                if re.search(r'[\u0000-\u0008\uf000-\uf8ff]|\b[A-Za-z]+ÿ',u['reading_text']):issues.append('source_character_artifact')
                claims.append(dict(record_type='expansion_candidate',schema_version='1.0.0',id=identifier,document_id=d['document_id'],
                    event_id=d['event_id'],actor_id=d['actor_id'],actor_role=d['actor_role'],lens_id=lens['id'],text_sha256=d['text_sha256'],
                    start=u['start'],end=u['end'],exact_passage=text[u['start']:u['end']],reading_text=u['reading_text'],
                    source_indices=u['source_indices'],quality_issues=sorted(set(issues)),selection_kind='retrieved_candidate',
                    origin='retrieval_not_prediction',scoring_eligible=False,training_approved=False))
    return claims,segments


def screen_retrieval(claims):
    accepted=[];rejected=[]
    patterns={
      'territorial_recognition':r'territori|sovereign|annex|border|souverain|fronti|территори|суверен|аннекс|границ',
      'troop_withdrawal':r'withdraw|retrait|retir|leave.*territor|end.*occupation|вывод|вывест|оккупа',
      'military_assistance':r'security assistance|military (?:aid|assistance|support)|(?:provid|supply|deliver|send|refus|suspend|condition|support).{0,75}(?:weapons|arms|military)|(?:weapons|arms).{0,75}(?:provid|supply|deliver|send|refus|support)|aide militaire|fourn.{0,60}(?:armes|militaire)|оруж|вооруж.*помощ',
      'sanctions':r'sanctions|restrictive measures|economic restrictions|санкц',
      'invasion_responsibility':r'aggress|invas|attack|used force|military intervention|responsib|blam|agress|invasion|агресс|напад|вторжен|операци|винов'}
    for source in claims:
        c=dict(source);reading=c['reading_text'];reason=None
        other=re.search(r'(?i)Gaza|Afghanistan|Syria|North Korea|Western Sahara|Taiwan|Palestin|Cuba|Venezuela|Zimbabwe|Israel',reading)
        if other and (not CONFLICT.search(reading) or re.search(r'(?i)Israel.{0,150}Gaza',reading)):
            reason='Explicit other-conflict subject; nearby/comparative Ukraine mention does not establish this target.'
        elif c.get('lens_id') and not re.search(patterns[c['lens_id']],reading,re.I):
            reason='Broad keyword hit lacks policy-specific formulation for this lens; retain for retrieval diagnostics, without assigning a stance.'
        if reason:
            c.update(retrieval_disposition='rejected_other_conflict' if other else 'rejected_policy_relevance',screening_reason=reason)
            rejected.append(c)
        else:
            c.update(retrieval_disposition='quarantined_source_review' if c['quality_issues'] else 'development_or_blind_review',
                screening_reason='Ukraine conflict context and policy-specific wording checked; source/attribution holds retained. No stance inferred.')
            accepted.append(c)
    return accepted,rejected


def packet_rows(docs,claims):
    prior=json.loads((ROOT.parent/'.local/development-review-v2/review_queue.json').read_text())
    returned=json.loads((ROOT.parent/'.local/workflow-returns/Badr_A-development-0001/returned_rows.json').read_text())
    new_annotations=json.loads((ROOT.parent/'.local/workflow-returns/Badr_A-development-0001/annotations.json').read_text())
    anns={a['claim_id']:a for a in new_annotations};by_return={r['candidate_id']:r for r in returned}
    rows=[]
    for r in prior:
        row=dict(r);a=anns[row['candidate_id']];response=by_return[row['candidate_id']]
        row['existing_annotation_id']=a['id'];row['existing_label']=a['label']
        row['existing_provenance']='Badr_A, AI-assisted preparation and reported additional checks; reviewed_non_independent, independent_human=false. Additional checks were not mapped to specific records.'
        row['existing_review_notes']=a['review_notes']+'\nSeparate returned quality decisions: '+json.dumps({k:v for k,v in response.items() if k.startswith('human_') and k not in ('human_label','human_annotator_id','human_review_notes','human_independent')},ensure_ascii=False)
        # Keep earlier history verbatim as an additional immutable audit field.
        row['prior_annotation_history']=json.dumps({k:r[k] for k in ('existing_annotation_id','existing_label','existing_provenance','existing_review_notes')},ensure_ascii=False)
        row['actor_role']='focal';row['selection_method']='pilot_purposive';row['imported_review_id']='Badr_A-development-0001'
        for key in RESPONSE_FIELDS:row[key]='false' if key=='human_independent' else ''
        rows.append(row)
    index={d['document_id']:d for d in docs};related=defaultdict(list)
    for c in claims:related[(c['document_id'],c['start'],c['end'])].append(c['id'])
    for c in claims:
        d=index[c['document_id']]
        if d['event_role']=='evaluation_reserved':continue
        adapted=dict(d,id=d['document_id']);event=dict(id=d['event_id'],event_date=d['event_date'])
        row=task(adapted,event,c,(OUT/d['text_path']).read_text(),'X-'+c['id'][-12:],[x for x in related[(c['document_id'],c['start'],c['end'])] if x!=c['id']])
        row.update(event_role='development_only',quarantine='true' if c['quality_issues'] else 'false',quality_flags=';'.join(c['quality_issues']),
            reading_text=c['reading_text'],source_qualification=' | '.join(filter(None,[d['translation_provenance'],d['prepared_statement_qualification'],d['rights_status'],d['actor_role']+' | '+d['selection_method']+' | Not representative country-period sampling'])),
            existing_annotation_id='',existing_label='',existing_provenance='',existing_review_notes='',selection_method=d['selection_method'],
            ai_suggested_label='',ai_rationale='',ai_review_flags='',prior_annotation_history='',actor_role=d['actor_role'],imported_review_id='')
        for key in RESPONSE_FIELDS:row[key]='false' if key=='human_independent' else ''
        rows.append(row)
    # Same columns, same types as the hash-protected CSV return contract.
    keys=list(dict.fromkeys(k for r in rows for k in r))
    rows=[{k:r.get(k,'') for k in keys} for r in rows]
    return rows


def build():
    if not (OUT/'catalog.json').exists():
        prior=ROOT.parent/'.local/expansion-v5'
        if not (prior/'catalog.json').exists():raise ValueError('Run expansion_collect, policy_search and targeted_collect first')
        for name in ('raw','cache','text','items'):shutil.copytree(prior/name,OUT/name,dirs_exist_ok=True)
        for name in ('catalog.json','outcomes.json','targeted_collection_outcomes.json'):shutil.copyfile(prior/name,OUT/name)
    roles=event_roles();docs=clear_catalog(json.loads((OUT/'catalog.json').read_text()))
    roles.update({d['event_id']:d['event_role'] for d in docs})
    write_immutable(OUT/'effective_event_split.json',dict(event_roles=roles,policy='Evaluation reservation wins across any subsequently discovered exact-copy cluster.',suggestions_generated=False))
    retrieved,segments=retrieve(docs);claims,rejected=screen_retrieval(retrieved)
    write_immutable(OUT/'retrieval_diagnostics.json',rejected)
    validate_expansion(docs,claims+rejected,roles)
    write_immutable(OUT/'cleared_catalog.json',docs);write_immutable(OUT/'candidates.json',claims);write_immutable(OUT/'segments.json',segments)
    rows=packet_rows(docs,claims)
    reserved={e for e,r in roles.items() if r=='evaluation_reserved'}
    reserved|=set(json.loads((ROOT/'workflow/v1/event_split.json').read_text())['reserved_event_ids'])
    if any(r['event_id'] in reserved for r in rows):raise ValueError('Evaluation event leaked into development packet')
    if len({r['candidate_id'] for r in rows})!=len(rows):raise ValueError('Duplicate packet candidate')
    packet=digest(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode())
    write_immutable(PACKET/'review_queue.json',rows);write_csv(PACKET/'orbit-development-review.csv',rows)
    render(PACKET/'orbit-development-review.html',rows,packet)
    manifest=dict(version='development-expansion-1.1.0',packet_id=packet,records=len(rows),preserved_reviewed_records=68,
        new_records=len(rows)-68,mechanically_clean=sum(r['quarantine']=='false' for r in rows),
        new_clean_records=sum(r['quarantine']=='false' and not r['existing_annotation_id'] for r in rows),
        quarantined=sum(r['quarantine']=='true' for r in rows),evaluation_records=0,
        events=sorted({r['event_id'] for r in rows}),reserved_event_ids=sorted(reserved),
        files={n:digest((PACKET/n).read_bytes()) for n in ('review_queue.json','orbit-development-review.csv','orbit-development-review.html')})
    write_immutable(PACKET/'manifest.json',manifest);write_immutable(ROOT/'workflow/development-expanded-v2-20261023/manifest.json',manifest)
    verified=[d for d in docs if not d['duplicate_of'] and d['event_identity_verified']]
    report=dict(goal_additional_focal_events=40,verified_additional_focal_events=sum(d['actor_role']=='focal' for d in verified),
        auxiliary_events=sum(d['actor_role']=='auxiliary_training_only' for d in verified),events_by_actor=dict(Counter(d['actor_id'] for d in verified)),
        years_by_actor={a:sorted({d['year'] for d in verified if d['actor_id']==a}) for a in sorted(ACTORS)},
        collection_streams=dict(Counter(d['selection_method'] for d in verified)),
        reserved_events_collected=sum(d['event_role']=='evaluation_reserved' for d in verified),
        candidates=len(claims),rejected_retrieval_candidates=len(rejected),retrieval_screened_pairs=len(retrieved),development_candidates=len(rows)-68,evaluation_candidates=sum(c['event_id'] in reserved for c in claims),
        candidate_events_by_actor={a:len({c['event_id'] for c in claims if c['actor_id']==a}) for a in sorted(ACTORS)},
        actor_lens_candidate_counts={a:dict(Counter(c['lens_id'] for c in claims if c['actor_id']==a)) for a in sorted(ACTORS)},
        quality_holds=dict(Counter(flag for c in claims for flag in c['quality_issues'])),
        wrong_attachment_mirrors=[dict(document_id=d['document_id'],duplicate_of=d['duplicate_of'],issues=d['quality_issues']) for d in docs if d['duplicate_of']],
        approved_training_labels=0,independent_human_annotations=0,independent_human_labeled_events=0,
        returned_reviewed_labels=dict(Counter(a['label'] for a in json.loads((ROOT.parent/'.local/workflow-returns/Badr_A-development-0001/annotations.json').read_text()))),
        source_clearance='Official archive provenance and event headings verified. EU common-position, translations, OCR, attribution and rights holds remain separate; no blanket scoring clearance.',
        evaluation_policy='Reservations frozen before collection; no AI suggestions or human labels generated for reserved events.',
        training_executed=False,public_scores_changed=False)
    write_immutable(OUT/'readiness.json',report);write_immutable(ROOT/'data/expansion-v6/readiness.json',report)
    write_immutable(ROOT/'schemas/expansion-v1/document.schema.json',DOC_SCHEMA)
    write_immutable(ROOT/'schemas/expansion-v1/candidate.schema.json',CANDIDATE_SCHEMA)
    print(json.dumps(dict(report=report,packet=manifest),indent=2))

if __name__=='__main__':build()
