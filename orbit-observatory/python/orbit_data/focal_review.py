"""Supplemental clean development evidence, separate from the frozen 561 packet."""
import json,re
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from .focal_retrieval import OUT,OLD,historical_metadata
from .validation import ROOT,digest,load_config
from .collect import write_json,utcnow
from .acquisition_sprint import PATTERNS,ANCHOR,RUSSIA,military_recipient_is_ukraine
from .sprint_review import Groups,compact,extra_gates,suggest,checkpoint_csv
from .resegment import sentence_windows,source_lines,units
from .development_review import render
from .workflow import QUALITY_RESPONSE_OPTIONS,write_csv

PACKET=ROOT.parent/'.local/development-review-focal-v2'
LENSES=load_config()[1]
VERSION='focal-admission-review-2.1.0'

def write_table(path,rows):
    if not rows:return
    if path.exists():
        if path.read_bytes():write_json(OUT/'table_history'/(digest(path.read_bytes())+'.json'),dict(name=path.name,sha256=digest(path.read_bytes())))
        path.unlink()
    write_csv(path,rows)

def scope_complete(p):
    return bool(re.search(r'Ukrain[^.!?]{0,150}internationally recogni[sz]ed (?:borders|boundaries|territor)|internationally recogni[sz]ed (?:borders|boundaries|territor)[^.!?]{0,70}Ukrain|(?:entire|all|whole)\s+(?:of\s+)?(?:Ukrainian territory|territory of Ukraine)',p,re.I|re.S))

def windows(text,start):
    # HTML source whitespace and PDF physical lines are not sentence boundaries.
    # Reuse the existing mapped reconstruction, retaining original envelopes.
    ls=[l for l in source_lines(text) if not re.fullmatch(r'EUCO \d+/\d+|EN|Conclusions\s*[–-].*',l['text'].strip())]
    for u in units(text,ls,body_start=start)[0]:
        if 55<=u['end']-u['start']<=2600:yield u['start'],u['end']

def speaker_for(d,text,a):
    if d['source_type']=='mea' and re.search(r'/(?:lok-sabha|rajya-sabha)\?',d.get('canonical_url','')):
        answer=re.search(r'(?:^|\n)\s*ANSWER\s*(?:\n|$)',text)
        if not answer or a<answer.end():return 'Parliamentary question / unverified turn','question_or_unverified_speaker_not_actor_position'
        return 'Official ministerial written answer identified after ANSWER marker',None
    if d['source_type']=='mea' and re.search(r'interview',d['title'],re.I):
        turns=[m for m in re.finditer(r'(?:^|\n)\s*(Q(?:uestion)?|A(?:nswer)?|EAM|Interviewer|Minister|Dr\.? S\.? Jaishankar)\s*:',text[:a+220],re.I) if m.start()<=a]
        if not turns:return d['speaker'],'speaker_turn_unresolved'
        name=turns[-1][1]
        if name.casefold() in ('q','question','interviewer'):return name,'question_or_unverified_speaker_not_actor_position'
        return name+' (interview answer by named Indian minister)',None
    if d['source_type']=='mfa' and re.search(r'Interview',d['title'],re.I):
        turns=[m for m in re.finditer(r'(?:^|\n)(FOREIGN MINISTER[^\n:–-]{0,110}|PRESENTER|QUESTION|INTERVIEWER)\s*[:–-]',text[:a+220],re.I) if m.start()<=a]
        if not turns:return d['speaker'],'speaker_turn_unresolved'
        name=turns[-1][1]
        return (name,None) if name.upper().startswith('FOREIGN MINISTER') else (name,'question_or_unverified_speaker_not_actor_position')
    if d['source_type']!='mea':return d['speaker'],None
    has_turns=re.search(r'(?:^|\n)(?:Prime Minister|President|Official Spokesperson|Foreign Secretary|Secretary \(|EAM|Question)[^\n:]{0,130}:',text,re.I)
    if not re.search(r'transcript|briefing',d['title'],re.I) and not has_turns:return d['speaker'],None
    turns=[m for m in re.finditer(r'(?:^|\n)([^\n:]{2,180}):',text[:a+200]) if m.start()<=a]
    if not turns:return d['speaker'],'speaker_turn_unresolved'
    name=turns[-1][1]
    if re.search(r'Foreign Secretary|Official Spokesperson|External Affairs Minister|Secretary \(|Prime Minister[^:]{0,70}Narendra Modi',name,re.I) and not re.search(r'Obama|Biden|Zelensk|Putin|Yatsenyuk|Russian|Ukrainian',name,re.I):return name,None
    return name,'question_or_unverified_speaker_not_actor_position'

def source_groups(docs):
    old_docs=historical_metadata();group=Groups([d['id'] for d in docs]);seen={};links=[]
    by_day=defaultdict(list)
    for d in old_docs:by_day[(d['actor_id'],d['event_date'])].append(d)
    reserved_hashes={d['text_sha256'] for d in old_docs if d['event_role']=='evaluation_reserved'}
    reserved_urls={d['canonical_url'].rstrip('/') for d in old_docs if d['event_role']=='evaluation_reserved' and d.get('canonical_url')}
    prior_shingles=defaultdict(set)
    for name in ['clean.json','held.json']:
        for p in json.loads((OLD/name).read_text()):
            if p['event_role']!='development_only':raise ValueError('Prior passage index must exclude reserved evidence')
            words=compact(p['exact_passage']).split()
            for i in range(max(0,len(words)-79)):prior_shingles[digest(' '.join(words[i:i+80]).encode())].add(p.get('leakage_group_id'))
    for d in docs:
        raw=(OUT/d['source_receipt']['raw_path']).read_bytes()
        if digest(raw)!=d['source_receipt']['raw_sha256']:raise ValueError('Original receipt hash mismatch')
        text=(OUT/d['text_path']).read_text()
        if digest(text.encode())!=d['text_sha256']:raise ValueError('Source text changed')
        if 'CHECK AGAINST DELIVERY' in text:
            d['source_publication_form']='Official prepared transcript marked CHECK AGAINST DELIVERY; actual delivery not independently verified'
            if 'CHECK AGAINST DELIVERY' not in d['translation_provenance']:d['translation_provenance']+='; CHECK AGAINST DELIVERY: prepared text, verbatim delivery not independently verified'
        if re.search(r'English translation',d['title'],re.I):
            d['translation_status']='Publisher-identified English translation; original not collected or independently compared'
            if 'Publisher-identified English translation' not in d['translation_provenance']:d['translation_provenance']+='; '+d['translation_status']
        # Remove verified repeated page title/navigation from candidate windows,
        # without changing source bytes or stored normalized text.
        last=text.rfind(d['title'])
        if last>=0:d['body_start']=last+len(d['title'])
        if d['source_type']=='mea' and re.search(r'/(?:lok-sabha|rajya-sabha)\?',d['canonical_url']):
            answer=re.search(r'(?:^|\n)\s*ANSWER\s*(?:\n|$)',text)
            if answer:d['body_start']=max(d['body_start'],answer.end());d['speaker']='Official ministerial written answer, excluding the preceding parliamentary question'
        if d['source_type']=='council':d['body_start']=0
        d['publisher']=urlsplit(d['canonical_url']).hostname
        if d['source_type']=='govza' and re.search(r'Western Cape|Provincial|Premier |municipal',d['title'],re.I):
            d['issuer']='Western Cape / provincial government office identified in article title'
            d['source_quality_flags']=sorted(set(d['source_quality_flags'])|{'subnational_or_nonexecutive_institutional_scope'})
        previous=by_day[(d['actor_id'],d['event_date'])]
        d['known_event_family']=bool(previous)
        if previous:
            d['prior_event_ids']=sorted({x['event_id'] for x in previous})
            d['event_role']='evaluation_reserved' if any(x['event_role']=='evaluation_reserved' for x in previous) else 'development_only'
            d['prior_group_ids']=sorted({x['leakage_group_id'] for x in previous})
        keys=[('date',d['actor_id'],d['event_date']),('body',digest(compact(text[d['body_start']:]).encode()))]
        inherited=set()
        # Policy-bearing paragraph overlaps, not unrelated site chrome/footer.
        for a,b in windows(text,d['body_start']):
            p=text[a:b]
            if not ANCHOR.search(p):continue
            words=compact(p).split()
            hashes=[digest(' '.join(words[i:i+80]).encode()) for i in range(max(0,len(words)-79))]
            keys.extend(('overlap',h) for h in hashes)
            for h in hashes:inherited.update(prior_shingles.get(h,set()))
        inherited.discard(None)
        explicit_reserved=d['text_sha256'] in reserved_hashes or d['canonical_url'].rstrip('/') in reserved_urls or any(x['event_role']=='evaluation_reserved' for x in previous)
        if explicit_reserved:d['event_role']='evaluation_reserved'
        if inherited:
            d['known_event_family']=True;d['prior_group_ids']=sorted(set(d.get('prior_group_ids',[]))|inherited)
            # Prior development exposure fixes a copied-text family's partition;
            # an explicitly known reserved match still takes precedence.
            if not explicit_reserved:d['event_role']='development_only'
        for k in keys:
            if k in seen:
                if group.find(d['id'])!=group.find(seen[k]):links.append(dict(a=d['id'],b=seen[k],basis=k[0]))
                group.union(d['id'],seen[k])
            else:seen[k]=d['id']
    reserved={group.find(d['id']) for d in docs if d['event_role']=='evaluation_reserved'}
    anchors=defaultdict(set)
    for d in docs:anchors[group.find(d['id'])].update(d.get('prior_group_ids',[]))
    for d in docs:
        anchor=anchors[group.find(d['id'])]
        d['leakage_group_id']=next(iter(anchor)) if len(anchor)==1 else 'focus2-group-'+digest(group.find(d['id']).encode())[:24]
        if group.find(d['id']) in reserved:d['event_role']='evaluation_reserved'
    write_json(OUT/'group_links.json',links);write_json(OUT/'source_event_manifest.json',docs)
    write_json(OUT/'split_assignments.json',{d['id']:dict(event_id=d['event_id'],group_id=d['leakage_group_id'],role=d['event_role'],prior_event_ids=d.get('prior_event_ids',[])) for d in docs})
    return docs

def relevant(lens,p,context,event_date):
    local=p+' '+context
    if not ANCHOR.search(local):return False
    if lens=='territorial_recognition':
        if not ANCHOR.search(p) and re.search(r'Indo.?Pacific|connectivity|\bmy borders\b|\bour borders\b|Pakistan|Taiwan|Nuclear Suppliers|West Asia|Palestin|Afghan|Gaza|Kashmir',p,re.I):return False
        different_object=re.search(r'territorial integrity of (?:Syria|Afghanistan|Pakistan|China|India|Turkey|Türkiye)|(?:Syrian|Afghan|Palestinian|Chinese|Pakistani) (?:sovereignty|territorial integrity)',p,re.I)
        ukrainian_object=re.search(r'Ukraine[’\']s[^.!?]{0,50}(?:sovereignty|territorial integrity)|(?:sovereignty|territorial integrity)[^.!?]{0,50}of Ukraine',p,re.I)
        if different_object and not ukrainian_object:return False
        # Annexure is not annexation; recognizing an achievement is not legal
        # territorial recognition; crossing a border is not a sovereignty claim.
        return bool(re.search(r'territorial integrity|sovereignty|\bannex(?:ation|ed|ing|s)?\b|internationally recogni[sz]ed (?:borders|boundaries)|inviolability of (?:the )?borders|chang\w*[^.!?]{0,45}borders[^.!?]{0,45}force|recogni[sz]\w*[^.!?]{0,90}(?:annexation|Crimea|Sevastopol|Donetsk|Luhansk|sovereignty|Ukrainian territory)',p,re.I|re.S))
    if lens=='troop_withdrawal':return bool(re.search(r'(?:Russia|Russian)[^.!?]{0,130}withdraw|withdraw[^.!?]{0,130}(?:Russia|Russian)',p,re.I|re.S))
    if lens=='military_assistance':return military_recipient_is_ukraine(p)
    if lens=='sanctions':
        policy=re.search(r'(?:impos|adopt|expand|maintain|extend|enforc|lift|remove|oppose|reject|support|welcome|introduc|announce)[^.!?]{0,90}(?:sanction|restrictive|export control)|(?:sanction|restrictive)[^.!?]{0,90}(?:impos|maintain|lift|remove|should|must|oppose|support|remain|adopt|extend|reject)',p,re.I|re.S)
        return bool(RUSSIA.search(local) and policy)
    if event_date<'2022-02-24':return False
    if not ANCHOR.search(p):
        if re.search(r'Tsarist|Caucasus|nineteenth|19th century|1944|Second World War|World War II|Afghanistan|Palestine|Gaza',p,re.I):return False
        if not re.search(r'\b(?:this|that|its|the) (?:illegal |unprovoked )?(?:invasion|war|aggression)\b',p,re.I):return False
    if re.search(r'(?:\bNATO\b|\bthe West\b)[^.!?]{0,130}(?:caused|provoked|led to|responsib|avoided)|(?:war|invasion)[^.!?]{0,80}avoided[^.!?]{0,130}\bNATO\b',p,re.I|re.S):return True
    if re.search(r'(?:Russia|Russian|Kremlin|Putin)[^.!?]{0,110}(?:invasion|aggression|launched|initiated)|(?:invasion|aggression)[^.!?]{0,110}(?:Russia|Russian|Kremlin|Putin)',p,re.I|re.S):return True
    return event_date=='2022-02-24' and bool(re.search(r'Russian[^.!?]{0,100}military operation[^.!?]{0,80}(?:launch|Ukraine)|military operation[^.!?]{0,80}Russian[^.!?]{0,70}Ukraine|Russian[^.!?]{0,100}attack[^.!?]{0,60}Ukraine',p,re.I|re.S))

def candidate(d,text,a,b,lens):
    return dict(candidate_id='claim-focus2-'+digest(f"{d['id']}:{a}:{b}:{lens}".encode()),document_id=d['id'],event_id=d['event_id'],event_role=d['event_role'],actor_id=d['actor_id'],actor_role='focal',event_date=d['event_date'],lens_id=lens,proposition=LENSES[lens]['definition'],issuer=d['issuer'],speaker=d['speaker'],source_url=d['canonical_url'],language=d['language'],translation_provenance=d['translation_provenance'],text_sha256=d['text_sha256'],start=a,end=b,exact_passage=text[a:b],context_before=text[max(0,a-500):a],context_after=text[b:b+350],quality_flags=list(d['source_quality_flags']),human_label='',annotator_id=None,training_approved=False,acquisition_method=d['acquisition_method'],source_text_path=str(OUT/d['text_path']),new_source_document=True,acquisition_kind='newly_collected',leakage_group_id=d['leakage_group_id'],known_event_family=d['known_event_family'])

def reading_map(text,a,b,council=False):
    ignored=set()
    if council:
        for m in re.finditer(r'[^\n]+',text[a:b]):
            if re.fullmatch(r'EUCO \d+/\d+|EN|[1-9]\d?|Conclusions\s*[–-].*',m.group().strip()):ignored.update(range(a+m.start(),a+m.end()))
    chars=[];indices=[]
    for i in range(a,b):
        if i in ignored:continue
        c=' ' if text[i].isspace() else text[i]
        if c==' ' and (not chars or chars[-1]==' '):continue
        chars.append(c);indices.append(i)
    if chars and chars[-1]==' ':chars.pop();indices.pop()
    return ''.join(chars),indices

def assess(r,d,text):
    p=r['exact_passage'];flags=set(r['quality_flags']);reject=None
    if not relevant(r['lens_id'],p,r['context_before'][-350:],r['event_date']):return flags,'wrong_conflict_or_policy_target'
    if re.search(r'^(?:No:|QA[-:]|SC[-:]|QUESTION|Click here|Latest Press|Press Release|Read the)',p,re.I) and not re.search(r'\b(?:we|Türkiye|Turkey|India|South Africa|European Council)\b.{0,80}\b(?:support|oppose|reject|call|condemn|reiterate|will|must|should)',p,re.I):return flags,'heading_or_navigation_not_policy_claim'
    speaker,problem=speaker_for(d,text,r['start']);r['speaker']=speaker
    if problem:flags.add(problem)
    if re.search(r'joint (?:statement|declaration|communiqu[eé])',d['title'],re.I) and d['actor_id']=='IND':
        other=re.match(r'\s*(?:\d+[.)]\s*)?(?:The (?:Italian|French|German|Ukrainian|Russian|European|British) side|The Nordic Prime Ministers|Italy|France|Germany|Ukraine|Russia|The European Union|The United States)\s+(?:reiterat\w*|stress\w*|condemn\w*|reaffirm\w*|stat\w*|emphasiz\w*|underlin\w*|express\w*|welcom\w*|not\w*)',p,re.I)
        if other:return flags,'explicit_partner_only_clause_not_Indian_position'
        if re.search(r'\b(?:most members|some members|other members|some countries|other views)\b',p,re.I):flags.add('collective_subset_not_explicit_actor_endorsement')
    if re.search(r'Western Cape|Provincial|Premier |municipal|Leader of the Opposition',d['title'],re.I):flags.add('subnational_or_nonexecutive_institutional_scope')
    if re.search(r'joint (?:statement|declaration|communiqu[eé])',d['title'],re.I):
        party={'TUR':r'Türkiye|Turkey|Erdo[ğg]an|Hakan Fidan','IND':r'Prime Minister[^.!?]{0,90}(?:Narendra )?Modi|India and Ukraine|India-Ukraine','ZAF':r'South Africa|Ramaphosa|Lamola|Pandor','EU':r'European Union|European Council'}[d['actor_id']]
        intro=text[d.get('body_start',0):d.get('body_start',0)+1000]
        if not re.search(party,d['title']+' '+intro,re.I):flags.add('joint_signatory_attribution_review')
    q=re.search(r'\b(?:said|according to|quoted|told|stated)\b',p,re.I)
    official_intro=re.search(r'(?:Official Spokesperson|Foreign Secretary|Minister)[^\n]{0,160}said:',text[max(0,r['start']-800):r['start']],re.I)
    own_zaf=re.search(r'(?:President (?:Cyril )?Ramaphosa|Minister (?:Naledi Pandor|Ronald Lamola)|Deputy President[^.!?]{0,40}Mashatile)[^.!?]{0,55}(?:said|stated|told|reiterated)|(?:said|stated)[^.!?]{0,40}(?:President (?:Cyril )?Ramaphosa|Minister (?:Naledi Pandor|Ronald Lamola))',p,re.I)
    own_india=d['actor_id']=='IND' and re.search(r'(?:Prime Minister[^.!?]{0,45}Modi|External Affairs Minister[^.!?]{0,45}Jaishankar|Official Spokesperson[^.!?]{0,45}(?:Jaiswal|Bagchi))[^.!?]{0,55}(?:said|stated|told|reiterated)',p,re.I)
    if q and not official_intro and not own_zaf and not own_india:flags.add('reported_speaker_review')
    if re.search(r'(?:Russia|Putin|Kremlin) (?:says|claims|argues|insists|demands|believes|has said)',p,re.I):flags.add('reported_foreign_position_attribution_review')
    if r['lens_id']=='territorial_recognition' and not (scope_complete(p) and re.search(r'illegal annex|(?:not|never|non)[ -]?(?:recogni|accept)',p,re.I)):flags.add('partial_territorial_scope')
    if r['lens_id']=='troop_withdrawal' and not scope_complete(p):flags.add('W1_legal_territorial_extent_review')
    if r['lens_id']=='troop_withdrawal' and re.search(r'pre[ -]?(?:24|February)|except.{0,25}Crimea',p,re.I):flags.add('W1_territorial_exception_or_preinvasion_line')
    if r['lens_id']=='military_assistance' and re.search(r'there is a huge effort to get the American|there are other works[^.!?]{0,80}European friends',p,re.I):flags.add('described_third_party_assistance_no_own_direction')
    if not re.search(r'[.!?][”"\')\]]?\s*$',p.strip()):flags.add('incomplete_sentence_boundary')
    if re.search(r'We hope|we call|we support|we reject|we condemn',p,re.I) and d['actor_id']=='IND' and re.search(r'\b(?:Suhasini|Nayanima|Sidhant)\s*:',p):flags.add('question_or_unverified_speaker_not_actor_position')
    return flags,reject

def prepare():
    docs=source_groups([json.loads(p.read_text()) for p in sorted((OUT/'documents').glob('*.json'))]);bydoc={d['id']:d for d in docs}
    original_clean=json.loads((OLD/'clean.json').read_text());original_held=json.loads((OLD/'held.json').read_text())
    old_review=json.loads((ROOT.parent/'.local/development-review-expanded-v2-20261023/review_queue.json').read_text())
    old_keys={(r['lens_id'],compact(r['exact_passage'])):r['candidate_id'] for r in original_clean+old_review}
    # Historical held claims can be recovered, but collecting an identical copy
    # is not new evidence or a new review task.
    held_keys={(r['lens_id'],compact(r['exact_passage'])):r['candidate_id'] for r in original_held}
    clean=[];held=[];rejected=[];duplicates=[];reserved=[];pool=[]
    for d in docs:
        if d['event_role']=='evaluation_reserved':reserved.append({k:d[k] for k in ['id','actor_id','event_id','event_date','leakage_group_id','canonical_url']});continue
        if d['duplicate_of']:duplicates.append(dict(document_id=d['id'],duplicate_of=d['duplicate_of'],reason='existing_source_text'));continue
        text=(OUT/d['text_path']).read_text();ws=list(windows(text,d['body_start']));spans=set()
        for a,b in ws:
            p=text[a:b]
            for lens in LENSES:
                if d['event_date']<LENSES[lens]['applicable_from']:continue
                if relevant(lens,p,text[max(0,a-350):a],d['event_date']):spans.add((a,b,lens))
        # Complete scope definitions in immediately neighbouring source paragraphs.
        for a,b,lens in list(spans):
            if lens not in ('territorial_recognition','troop_withdrawal'):continue
            near=[(x,y) for x,y in ws if a-1200<=x<=b+1200]
            for x,y in near:
                if not scope_complete(text[x:y]):continue
                aa,bb=min(a,x),max(b,y)
                if bb-aa<=2600:spans.add((aa,bb,lens))
        for a,b,lens in sorted(spans):
            r=candidate(d,text,a,b,lens);flags,reject=assess(r,d,text);r['quality_flags']=sorted(flags)
            if reject:rejected.append(dict(candidate_id=r['candidate_id'],document_id=d['id'],start=a,end=b,lens_id=lens,reason=reject));continue
            pool.append(r)
    if (OUT/'recovered_candidates.json').exists():
        old_docs={d['id']:d for d in json.loads((OLD/'source_event_manifest.json').read_text())}
        rejection_ids={r['original_candidate_id'] for r in json.loads((OUT/'clearance_ledger.json').read_text()) if r['rejection']}
        recovered=json.loads((OUT/'recovered_candidates.json').read_text())
        if (OUT/'joint_recovered_candidates.json').exists():recovered+=json.loads((OUT/'joint_recovered_candidates.json').read_text())
        for r in recovered:
            if r['recovery_of'] in rejection_ids:continue
            r.update(acquisition_kind='recovered_held',known_event_family=True,leakage_group_id=old_docs[r['document_id']]['leakage_group_id'])
            # Use the documentary clearance flags rather than reapplying the old
            # coarse quotation/joint heuristics that caused those holds.
            d=old_docs[r['document_id']];text=Path(r['source_text_path']).read_text()
            if re.search(r'(?:independent )?experts (?:note|found|conclude)|(?:report|Commission of Inquiry) (?:notes|finds|says|concludes)|according to',r['exact_passage'],re.I):
                r['quality_flags']=sorted(set(r['quality_flags'])|{'reported_expert_finding_not_direct_issuer_stance'})
            if not relevant(r['lens_id'],r['exact_passage'],r['context_before'],r['event_date']):
                rejected.append(dict(candidate_id=r['candidate_id'],document_id=r['document_id'],reason='recovery_still_wrong_policy_target'));continue
            pool.append(r)
    # Prefer the shortest complete equivalent over longer overlapping windows.
    pool.sort(key=lambda r:(bool(r['quality_flags']),r['end']-r['start'],r['candidate_id']))
    seen={};accepted_by_doc=defaultdict(list)
    for r in pool:
        key=(r['lens_id'],compact(r['exact_passage']))
        if key in old_keys:duplicates.append(dict(candidate_id=r['candidate_id'],duplicate_of=old_keys[key],reason='already_reviewed_or_in_frozen_561_packet'));continue
        if r['acquisition_kind']=='newly_collected' and key in held_keys:duplicates.append(dict(candidate_id=r['candidate_id'],duplicate_of=held_keys[key],reason='existing_held_passage_copy_not_new_evidence'));continue
        if key in seen:duplicates.append(dict(candidate_id=r['candidate_id'],duplicate_of=seen[key],reason='identical_passage_proposition'));continue
        # A broad repaired/context span is not an additional distinct claim when
        # a clean shorter span already supplies that same policy in this document.
        overlaps=[x for x in accepted_by_doc[(r['document_id'],r['lens_id'])] if x['start']<r['end'] and r['start']<x['end']]
        if overlaps:duplicates.append(dict(candidate_id=r['candidate_id'],duplicate_of=overlaps[0]['candidate_id'],reason='overlapping_same_document_lens_claim'));continue
        seen[key]=r['candidate_id']
        if r['quality_flags']:held.append(r)
        else:clean.append(r);accepted_by_doc[(r['document_id'],r['lens_id'])].append(r)
    for r in clean+held:
        text=Path(r['source_text_path']).read_text()
        if digest(text.encode())!=r['text_sha256'] or text[r['start']:r['end']]!=r['exact_passage']:raise ValueError('Offset/hash mismatch')
        # Complete surrounding stored blocks rather than arbitrary character
        # cuts. HTML block paragraphs remain intact; PDF physical paragraphs
        # may remain uncertain and their original line structure is preserved.
        cs=text.rfind('\n',0,max(0,r['start']-500))+1
        ce=text.find('\n',min(len(text),r['end']+500))
        if ce<0:ce=len(text)
        r['context_before']=text[cs:r['start']];r['context_after']=text[r['end']:ce]
        r['context_boundary_basis']='Whole adjacent stored blocks; source text unchanged; PDF paragraph geometry not inferred'
        r['reading_text'],r['reading_source_indices']=reading_map(text,r['start'],r['end'],r['actor_id']=='EU')
    for name,value in [('clean.json',clean),('held.json',held),('rejected.json',rejected),('duplicates.json',duplicates),('reserved_metadata.json',reserved)]:write_json(OUT/name,value)
    return docs,clean,held,rejected,duplicates,reserved

def proposal(r):
    label,rationale=suggest(r);p=re.sub(r'\s+',' ',r['exact_passage'])
    if r['lens_id']=='sanctions':
        m=re.search(r'\b(?:we|India|Türkiye|Turkey|South Africa).{0,45}(?:oppose|reject|against|do not support).{0,50}(?:unilateral )?sanctions',p,re.I)
        if m:label='oppose';rationale='Explicit rejection of the Russia/Ukraine-linked sanctions target: “'+m.group()+'”. Preserve measure type and any stated conditions.'
        elif re.search(r'\b(?:we|Council|European Union|United States|Treasury|OFAC)\b[^.!?]{0,90}\b(?:will maintain|will continue|have imposed|has imposed|adopted|imposed|will impose)\b[^.!?]{0,80}\b(?:sanctions|restrictive measures)',p,re.I):
            label='support';rationale='The attributable issuer commits to imposing or maintaining the Russia/Ukraine measures. Any condition is retained in the exact passage; it does not automatically imply mixed or opposition.'
    if r['lens_id']=='invasion_responsibility' and r['event_date']=='2022-02-24' and re.search(r'Russian.{0,100}military operation|military operation.{0,100}Russian',p,re.I):
        label='support';rationale='The dated 24 February 2022 statement identifies Russia’s military operation launched against Ukraine. This is explicit initiation attribution; the source term “operation” is preserved.'
    return label,rationale

def build():
    docs,clean,held,rejected,duplicates,reserved=prepare();rows=[];refs={};suggestions=[]
    for r in clean:
        label,rationale=proposal(r);start,end=r['start'],r['end']
        row=dict(queue_version=VERSION,record_type='annotation_task',row_id='F2-'+digest(r['candidate_id'].encode())[:12],candidate_id=r['candidate_id'],selection_kind=r['acquisition_kind'],passage_id='passage-'+digest(f"{r['document_id']}:{start}:{end}".encode()),related_candidate_ids='',event_id=r['event_id'],document_id=r['document_id'],actor_id=r['actor_id'],actor_role='focal',event_date=r['event_date'],lens_id=r['lens_id'],lens_proposition=LENSES[r['lens_id']]['definition'],source_url=r['source_url'],attachment_url='',document_issuer=r['issuer'],speaker=r['speaker'],language=r['language'],language_review_required='false',text_sha256=r['text_sha256'],start=str(start),end=str(end),exact_passage=r['exact_passage'],context_start=str(start-len(r['context_before'])),context_end=str(end+len(r['context_after'])),context_before=r['context_before'],context_after=r['context_after'],offset_unit='unicode_code_point_half_open',codebook_version='consolidated-v1',translation_aid_id='',label='',annotator_id='',review_status='',review_notes='',reading_text=r['reading_text'],source_qualification=r['translation_provenance']+'; '+r['acquisition_kind']+'; targeted training acquisition, not representative annual scoring.',quality_flags='',quarantine='false',mechanical_resolutions=';'.join(r.get('previous_quality_flags',[])),event_role='development_only',leakage_group_id=r['leakage_group_id'],revises_candidate_id=r.get('revises_candidate_id',''),recovery_of=r.get('recovery_of',''),attribution_evidence=r.get('attribution_evidence',''),shared_endorsing_actor_ids=';'.join(r.get('shared_endorsing_actor_ids',[])),priority=90 if label in ('unresolved','mixed','oppose') else 40,priority_reasons='ambiguity_or_contrast' if label in ('unresolved','mixed','oppose') else 'unreviewed_focal_evidence',existing_annotation_id='',existing_label='',existing_provenance='',existing_review_notes='',ai_suggested_label=label,ai_rationale=rationale,ai_review_flags=VERSION+'; assistant-authored deterministic source/proposition rules; not trained-model inference; no confidence or human check',human_label='',human_annotator_id='',human_review_notes='',human_independent='false',**{f:'' for f in QUALITY_RESPONSE_OPTIONS})
        rows.append(row);refs[r['candidate_id']]=r;suggestions.append(dict(candidate_id=r['candidate_id'],label=label,rationale=rationale,origin='ai_generated_unreviewed',method=VERSION,human_reviewed=False,training_approved=False))
        from .component_review import interpret,COMPONENT_TARGETS,VERSION as COMPONENT_VERSION
        v=interpret(r);r['experimental_components']=v
        row.update(component_protocol=COMPONENT_VERSION,component_proposition=COMPONENT_TARGETS[r['lens_id']],component_expression=v['expression'],component_scope=v['scope'],component_annexation=v['annexation'],component_conditions=v['conditions'],component_basis=v['basis'],strict_target_status='Source-cleared full-target review candidate; no approved stance label',experimental_component_direction=v['direction'])
    shared=defaultdict(list)
    for r in rows:shared[r['passage_id']].append(r['candidate_id'])
    for r in rows:r['related_candidate_ids']=';'.join(x for x in shared[r['passage_id']] if x!=r['candidate_id'])
    rows.sort(key=lambda r:(-r['priority'],['IND','TUR','ZAF','EU','USA'].index(r['actor_id']),r['event_date'],r['row_id']))
    packet=digest(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode());PACKET.mkdir(exist_ok=True)
    old=json.loads((PACKET/'manifest.json').read_text()) if (PACKET/'manifest.json').exists() else {}
    for p in (ROOT.parent/'.local/workflow-returns').glob('*/ledger.json'):
        if old and json.loads(p.read_text()).get('baseline_sha256')==old['files']['review_queue.json'] and old['packet_id']!=packet:raise ValueError('Reviewed supplemental packet frozen; increment version')
    created=old.get('created_at',utcnow()) if old.get('packet_id')==packet else utcnow()
    write_json(PACKET/'review_queue.json',rows);write_table(PACKET/'orbit-development-review.csv',rows)
    p=PACKET/'orbit-development-review.html'
    if p.exists():p.unlink()
    render(p,rows,packet)
    write_json(PACKET/'source_refs.json',refs);write_json(PACKET/'ai_suggestions.json',suggestions)
    write_json(PACKET/'progress-backup.json',dict(format='orbit-development-responses-v2',packet_id=packet,saved_at=created,provenance='AI-generated unreviewed preparation; no Badr_A check or training authorization',settings={},responses={}))
    write_json(PACKET/'manifest.json',dict(version=VERSION,packet_id=packet,created_at=created,records=len(rows),mechanically_clean=len(rows),new_clean_records=len(rows),quarantined=0,events=sorted({r['event_id'] for r in rows}),evaluation_records=0,files={n:digest((PACKET/n).read_bytes()) for n in ['review_queue.json','orbit-development-review.csv','orbit-development-review.html','source_refs.json','ai_suggestions.json','progress-backup.json']}))
    write_json(OUT/'recovered_clean_ledger.json',[dict(candidate_id=r['candidate_id'],original_candidate_id=r['recovery_of'],document_id=r['document_id'],event_id=r['event_id'],prior_holds=r['previous_quality_flags'],remaining_holds=r['quality_flags'],revised_span=bool(r.get('revises_candidate_id')),human_review_required=True,annotation_transferred=False) for r in clean if r['acquisition_kind']=='recovered_held'])
    coverage=[]
    for actor in ['USA','EU','TUR','IND','ZAF']:
        for lens in LENSES:
            prior=[r for r in json.loads((OLD/'clean.json').read_text()) if r['actor_id']==actor and r['lens_id']==lens];added=[r for r in clean if r['actor_id']==actor and r['lens_id']==lens]
            coverage.append(dict(actor=actor,lens=lens,before_pairs=len(prior),before_events=len({r['event_id'] for r in prior}),before_groups=len({r['leakage_group_id'] for r in prior}),newly_collected_pairs=sum(r['acquisition_kind']=='newly_collected' for r in added),recovered_pairs=sum(r['acquisition_kind']=='recovered_held' for r in added),after_pairs=len(prior)+len(added),after_events=len({r['event_id'] for r in prior+added}),after_groups=len({r['leakage_group_id'] for r in prior+added}),supplement_events=len({r['event_id'] for r in added}),supplement_groups=len({r['leakage_group_id'] for r in added}),genuinely_new_event_families=len({r['event_id'] for r in added if not r['known_event_family']}),held_pairs=sum(r['actor_id']==actor and r['lens_id']==lens for r in held)))
    write_table(OUT/'coverage.csv',coverage);write_json(OUT/'coverage.json',coverage)
    report=dict(new_documents=len(docs),new_document_events=len({d['event_id'] for d in docs}),clean_pairs=len(clean),newly_collected_clean_pairs=sum(r['acquisition_kind']=='newly_collected' for r in clean),recovered_clean_pairs=sum(r['acquisition_kind']=='recovered_held' for r in clean),clean_passages=len({(r['document_id'],r['start'],r['end']) for r in clean}),supplement_events=len({r['event_id'] for r in clean}),supplement_groups=len({r['leakage_group_id'] for r in clean}),genuinely_new_clean_events=len({r['event_id'] for r in clean if not r['known_event_family']}),new_reserved_documents=len(reserved),held_pairs=len(held),rejected=len(rejected),duplicates=len(duplicates),by_actor={a:dict(pairs=sum(r['actor_id']==a for r in clean),new_pairs=sum(r['actor_id']==a and r['acquisition_kind']=='newly_collected' for r in clean),recovered_pairs=sum(r['actor_id']==a and r['acquisition_kind']=='recovered_held' for r in clean),events=len({r['event_id'] for r in clean if r['actor_id']==a})) for a in ['IND','TUR','ZAF','EU','USA']},by_lens=dict(Counter(r['lens_id'] for r in clean)),suggested_classes=dict(Counter(r['label'] for r in suggestions)),new_approved_labels=0,existing_eligible_examples=38,existing_eligible_events=8,suggestion_method=VERSION)
    write_json(OUT/'yield.json',report);print(json.dumps(report,indent=2));return report

if __name__=='__main__':build()
