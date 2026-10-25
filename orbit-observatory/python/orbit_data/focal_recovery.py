"""Append-only, documentary review of the held DEVELOPMENT set. No labels transferred."""
import json,re
from collections import Counter
from .focal_retrieval import OUT,OLD
from .validation import ROOT,digest
from .collect import write_json
from .workflow import write_csv
from .resegment import sentence_windows
from .acquisition_sprint import PATTERNS

TECH={'joint_signatory_attribution_review','quoted_speaker_review','incomplete_sentence_boundary','PDF_cover_or_sentence_review','speaker_role_review','inline_word_boundary_extraction','EU_common_position_review','translation_review'}
SCOPE={'partial_territorial_scope','W1_scope_not_established','W1_legal_territorial_extent_review'}
POLICY={'Ukraine_sanctions_basis_not_local','sanctions_target_or_conflict_basis_review','legal_implementation_only'}

def complete(p):return bool(re.search(r'[.!?][”"\')\]]?\s*$',p.strip()))

def clear_claim(r,d,text):
    flags=set(r['quality_flags']);proofs=[];a,b=r['start'],r['end'];p=r['exact_passage'];original_flags=set(flags)
    def clear(flag,basis,pa=None,pb=None):
        if flag not in flags:return
        flags.remove(flag);pa=a if pa is None else pa;pb=b if pb is None else pb
        proofs.append(dict(previous_hold=flag,criterion=basis,source_url=d['canonical_url'],source_text_sha256=d['text_sha256'],proof_start=pa,proof_end=pb,proof_text=text[pa:pb],method='documentary cached-source review; no stance label or independent human check'))
    rejection=None
    if p.strip()==d['title'].strip() or (len(p)<220 and re.search(r'^(?:Read the|See also|Click |Related |SANCTIONS IMPLICATIONS)',p,re.I)):
        return None,[],dict(reason='heading_or_navigation_not_stance_evidence')
    if 'incomplete_sentence_boundary' in flags:
        # Trim an unfinished suffix only when complete source sentences retain
        # the lens claim. No guessed punctuation or rewritten source text.
        spans=[(x,y) for x,y in sentence_windows(p) if complete(p[x:y]) and re.search(PATTERNS[r['lens_id']],p[x:y],re.I)]
        if spans:
            a=r['start']+spans[0][0];b=r['start']+spans[-1][1];p=text[a:b]
            clear('incomplete_sentence_boundary','Complete retained source sentence; unfinished suffix excluded in a versioned span',a,b)
        else:
            # A physical PDF line can continue into the next stored line.
            tail=text[r['start']:min(len(text),r['end']+1000)]
            span=next(((x,y) for x,y in sentence_windows(tail) if y>=r['end']-r['start'] and complete(tail[x:y]) and re.search(PATTERNS[r['lens_id']],tail[x:y],re.I)),None)
            if span and len(tail[span[0]:span[1]])<=2200 and not re.search(r'\n(?:Q[.:]|Question:|[A-Z][a-z]+:)',tail[span[0]:span[1]]):
                a=r['start']+span[0];b=r['start']+span[1];p=text[a:b]
                clear('incomplete_sentence_boundary','Complete sentence reconstructed across physical stored lines; original text unchanged',a,b)
    if flags&SCOPE:
        # The approved clarification permits an explicit scope definition in
        # adjoining context. Include it in a new span; never supply it ourselves.
        lo=max(0,a-1400);hi=min(len(text),b+1400);near=text[lo:hi]
        scope=re.search(r'(?:Ukrain\w*[^.!?]{0,150}internationally recogni[sz]ed (?:borders|boundaries|territor)|internationally recogni[sz]ed (?:borders|boundaries|territor)[^.!?]{0,70}Ukrain)',near,re.I|re.S)
        if scope:
            pa=lo+scope.start();pb=lo+scope.end()
            aa=text.rfind('\n',0,min(a,pa))+1;bb=text.find('\n',max(b,pb))
            if bb<0:bb=len(text)
            # Start at a complete source sentence, not the final physical line
            # of the preceding sentence (e.g. "long as it takes.").
            from .resegment import units,source_lines
            for u in units(text,source_lines(text))[0]:
                if u['start']<aa<u['end']:
                    aa=u['start'];break
            expanded=text[aa:bb]
            if len(expanded)<=2800 and complete(expanded):
                if r['lens_id']=='troop_withdrawal' and re.search(r'(?:Russia|Russian)[^.!?]{0,120}withdraw|withdraw[^.!?]{0,120}Russian',expanded,re.I|re.S):
                    a,b,p=aa,bb,expanded
                    for f in ['W1_scope_not_established','W1_legal_territorial_extent_review']:clear(f,'New span includes the explicit Ukrainian recognized-border scope and Russian withdrawal wording under unchanged W1',aa,bb)
                elif r['lens_id']=='territorial_recognition' and re.search(r'illegal annex|(?:not|never|non)[ -]?(?:recogni|accept)',expanded,re.I):
                    a,b,p=aa,bb,expanded
                    clear('partial_territorial_scope','New span includes explicit comprehensive Ukrainian recognized borders and annexation non-recognition wording; strict target retained',aa,bb)
    if 'quoted_speaker_review' in flags and d['actor_id']=='USA' and d['source_type']=='treasury':
        q=re.search(r'\bsaid\s+(?:Acting\s+)?(?:(?:Under|Deputy|Assistant) Secretary(?: of the Treasury| for (?:Terrorism|International))|Treasury Secretary|Secretary of the Treasury|OFAC Director)[^“”\n]{0,140}',p)
        if q:clear('quoted_speaker_review','Same passage explicitly attributes the quotation to the issuing U.S. Treasury/OFAC office',a+q.start(),a+q.end())
        else:
            quoted=re.findall(r'“([^”]+)”|"([^"]+)"',p)
            if quoted and all(len(x or y)<65 and not re.search(r'[.!?]',x or y) for x,y in quoted) and not re.search(r'said|according to|claimed|alleged|wrote|told|proposed',p,re.I):
                clear('quoted_speaker_review','Quotation marks enclose short terms, not an attributed third-party assertion; institutional author remains speaker')
    if 'joint_signatory_attribution_review' in flags and d['actor_id']=='USA':
        # The previous title heuristic also flagged individual remarks/readouts
        # merely because the meeting name included G7/G20.
        if re.search(r'remarks by|statement by|readout|Secretary.*(?:meeting|call)|Deputy Secretary.*(?:meeting|call)',d['title'],re.I) and not re.search(r'joint statement|joint declaration|communiqu[eé]',d['title'],re.I):
            clear('joint_signatory_attribution_review','Title identifies U.S. Treasury individual remarks/readout at a G7/G20 event, not a jointly authored declaration',0,min(len(text),700))
        else:
            q=re.search(r'(?:Secretary|United States|U\.S\.).{0,100}(?:joined|issued|signed|endorsed).{0,100}(?:statement|communiqu[eé])',text,re.I)
            if q:clear('joint_signatory_attribution_review','Official article explicitly records U.S. participation in issuing/endorsing this joint statement',q.start(),q.end())
    if d['actor_id']=='IND' and d['source_type']=='mea':
        # Resolve the most recent named turn; publishing reporters is not endorsement.
        turns=list(re.finditer(r'(?:^|\n)([^\n:]{2,160}):',text[:b]))
        turn=next((m for m in reversed(turns) if m.start()<=a),None)
        if turn:
            name=turn[1]
            if re.search(r'Foreign Secretary|Official Spokesperson|External Affairs Minister',name,re.I):
                clear('speaker_role_review','Nearest preceding transcript turn identifies the authorized Indian official',turn.start(),turn.end())
                # Quoted question names within the official answer do not alone
                # permit clearing quotations; retain that separate hold.
            elif re.search(r'^\s*[A-Za-z][^:]{0,70}$',name) and not re.search(r'New Delhi|https|Note|Question|Answer',name,re.I):
                rejection=dict(reason='journalist_or_unverified_turn_not_Indian_official',speaker_marker=name)
        minister=re.search(r'(?:MINISTER OF STATE|MINISTER OF EXTERNAL AFFAIRS)[^\n]{0,180}',text,re.I)
        if minister and re.search(r'QUESTION|Q\.?NO|LOK SABHA|RAJYA SABHA',d['title'],re.I) and not re.search(r'\?\s*$',p):
            clear('speaker_role_review','Official parliamentary answer names the responsible government minister; not a legislator opinion',minister.start(),minister.end())
    if 'previously_collected_source_not_new' in flags:
        clear('previously_collected_source_not_new','This is source novelty, not a source-quality defect; prior reviewed/packet overlap is checked separately')
    revised=dict(r);changed=(a,b)!=(r['start'],r['end'])
    if re.match(r'^\s*[a-z]',text[a:b]):flags.add('incomplete_sentence_start')
    if changed:
        revised.update(candidate_id='claim-focus2-revision-'+digest(f"{r['candidate_id']}:{a}:{b}".encode()),revises_candidate_id=r['candidate_id'],revision_reason='Complete-source-sentence boundary repair; no annotation transfer',review_required=True)
    revised.update(start=a,end=b,exact_passage=text[a:b],context_before=text[max(0,a-500):a],context_after=text[b:b+350],quality_flags=sorted(flags),previous_quality_flags=sorted(original_flags),recovery_of=r['candidate_id'],source_text_path=str(OLD/d['text_path']),new_source_document=False,acquisition_method='cached_documentary_hold_recovery_v2',human_label='',annotator_id=None,training_approved=False)
    return revised,proofs,rejection

def audit():
    held=json.loads((OLD/'held.json').read_text());docs={d['id']:d for d in json.loads((OLD/'source_event_manifest.json').read_text())}
    ledger=[];candidates=[];audit_rows=[];scope=[];date_revisions=[]
    for r in held:
        if r['event_role']!='development_only' or docs[r['document_id']]['event_role']!='development_only':raise ValueError('Reserved evidence cannot enter recovery')
        flags=set(r['quality_flags']);cats=[]
        if flags&TECH:cats.append('A_technical_source')
        if flags&SCOPE:cats.append('B_target_scope_insufficient')
        if flags&POLICY:cats.append('B_policy_target_or_implementation_review')
        if 'legal_implementation_only' in flags:cats.append('C_endorsement_not_established_by_implementation')
        if 'reported_foreign_position_attribution_review' in flags:cats.append('A_attribution_or_D_wrong_speaker')
        if 'previously_collected_source_not_new' in flags:cats.append('D_prior_source_novelty_not_quality')
        audit_rows.append(dict(candidate_id=r['candidate_id'],actor=r['actor_id'],lens=r['lens_id'],categories=';'.join(cats),hold_reasons=';'.join(sorted(flags)),political_ambiguity_not_inferred_from_defect=True))
        if 'partial_territorial_scope' in flags:
            p=r['exact_passage'];uk=bool(re.search(r'Ukrain.{0,100}(?:territorial integrity|sovereignty)|(?:territorial integrity|sovereignty).{0,100}Ukrain',p,re.I|re.S))
            scope.append(dict(candidate_id=r['candidate_id'],actor=r['actor_id'],event_id=r['event_id'],source_url=r['source_url'],other_holds=';'.join(sorted(flags-{'partial_territorial_scope'})),Ukraine_integrity_direction_cue=uk,recognized_scope_cue=bool(re.search(r'internationally recogni[sz]ed|1991',p,re.I)),annexation_nonrecognition_cue=bool(re.search(r'(?:not|never|non)[ -]?(?:recogni|accept)|illegal annex',p,re.I)),named_scope=';'.join(n for n in ['Crimea','Sevastopol','Donetsk','Luhansk','Kherson','Zaporizhzhia'] if n.casefold() in p.casefold()),current_target_unchanged=True,component_judgment_status='proposal_only_no_new_labels'))
        if r['actor_id']=='GBR':continue # audit counts retained; no bulk auxiliary recovery
        d=docs[r['document_id']];text=(OLD/d['text_path']).read_text()
        assert digest(text.encode())==r['text_sha256'] and text[r['start']:r['end']]==r['exact_passage']
        revised,proofs,rejection=clear_claim(r,d,text)
        if d['actor_id']=='IND' and d['source_type']=='mea':
            from .focal_collection import date_value
            delivered=date_value(d['title'])
            if delivered and delivered!=d['event_date']:
                pa=text.find(d['title']);pb=pa+len(d['title'])
                if pa>=0:
                    finding=dict(document_id=d['id'],candidate_id=r['candidate_id'],previous_event_date=d['event_date'],corrected_delivery_date=delivered,publication_date=d['publication_date'],source_url=d['canonical_url'],source_text_sha256=d['text_sha256'],proof_start=pa,proof_end=pb,proof_text=text[pa:pb],method='Delivery date explicitly embedded in transcript title; publication retained separately',old_record_unchanged=True)
                    date_revisions.append(finding)
                    if revised:
                        revised.update(candidate_id='claim-focus2-date-'+digest(f"{r['candidate_id']}:{delivered}:{revised['start']}:{revised['end']}".encode()),previous_event_date=d['event_date'],event_date=delivered,revises_candidate_id=r['candidate_id'],revision_reason='Documentary delivery/publication date correction; original source/record and group preserved; no annotation transferred')
        if rejection:
            audit_rows[-1]['categories']+=';D_heading_or_wrong_speaker'
        if revised:candidates.append(revised)
        if proofs or rejection:
            record=dict(id='clearance-focus2-'+digest(r['candidate_id'].encode()),original_candidate_id=r['candidate_id'],replacement_candidate_id=revised['candidate_id'] if revised else None,original_holds=r['quality_flags'],clearances=proofs,remaining_holds=revised['quality_flags'] if revised else r['quality_flags'],rejection=rejection,stance_judgment_changed=False,annotation_transferred=False,independent_human_check_asserted=False,training_approved=False)
            ledger.append(record)
    lp=OUT/'clearance_ledger.json'
    if lp.exists():write_json(OUT/'clearance_ledger_history'/(digest(lp.read_bytes())+'.json'),json.loads(lp.read_text()))
    write_json(OUT/'hold_audit.json',audit_rows);write_json(lp,ledger);write_json(OUT/'recovered_candidates.json',candidates);write_json(OUT/'territorial_affected_records.json',scope)
    for name,rows in [('hold_audit.csv',audit_rows),('territorial_affected_records.csv',scope)]:
        target=OUT/name
        if target.exists():
            history=OUT/'audit_history';history.mkdir(exist_ok=True);(history/(digest(target.read_bytes())+'.csv')).write_bytes(target.read_bytes());target.unlink()
        write_csv(target,rows)
    result=dict(audited=len(held),overlapping_reasons=dict(Counter(f for r in held for f in r['quality_flags'])),overlapping_categories=dict(Counter(c for r in audit_rows for c in r['categories'].split(';') if c)),focal_candidates=len(candidates),clearance_records=len(ledger),partial_territorial_pairs=len(scope),direction_cues_with_no_other_holds=sum(r['Ukraine_integrity_direction_cue'] and not r['other_holds'] for r in scope))
    write_json(OUT/'document_date_revisions.json',date_revisions)
    write_json(OUT/'hold_audit_summary.json',result);print(json.dumps(result));return result



def audit_joint_parties():
    held=json.loads((OLD/'held.json').read_text())
    docs={d['id']:d for d in json.loads((OLD/'source_event_manifest.json').read_text())}
    recovered=[];ledger=[]
    selected={r['document_id'] for r in held if r['actor_id']=='GBR' and 'joint_signatory_attribution_review' in r['quality_flags']}
    for did in sorted(selected):
        d=docs[did]
        assert d['event_role']=='development_only'
        text=(OLD/d['text_path']).read_text()
        formula=re.search(r'we,?\s+(?:the\s+)?(?:G7\s+Foreign Ministers|leaders)[^.!?]{0,1100}|I am delivering this statement on behalf[^.!?]{0,1100}',text[:1800],re.I|re.S)
        if not formula:continue
        parties=formula.group();actors=[]
        if re.search(r'\bTürkiye\b|\bTurkey\b',parties):actors.append('TUR')
        if re.search(r'High Representative of the European Union|President of the European Council',parties):actors.append('EU')
        if re.search(r'United States',parties):actors.append('USA')
        if not actors:continue
        actor=actors[0] # One task per shared utterance; keep other party bindings.
        for original in held:
            if original['document_id']!=did:continue
            flags=set(original['quality_flags'])-{'joint_signatory_attribution_review'}
            input_record=dict(original,actor_id=actor,quality_flags=sorted(flags))
            revised,extra,rejection=clear_claim(input_record,dict(d,actor_id=actor),text)
            if rejection or revised is None:continue
            revised.update(candidate_id='claim-focus2-joint-'+digest(f"{original['candidate_id']}:{actor}:{revised['start']}:{revised['end']}".encode()),actor_role='focal',issuer='Named joint issuing parties, including '+','.join(actors),speaker='Explicit joint issuing-party/on-behalf-of formula',previous_quality_flags=original['quality_flags'],recovery_of=original['candidate_id'],revises_candidate_id=original['candidate_id'],revision_reason='Verified joint-party attribution and any documented span repair; no annotation transfer',acquisition_method='cached_explicit_joint_party_attribution_recovery',shared_endorsing_actor_ids=actors,publisher_actor_id='GBR',attribution_evidence=parties,translation_provenance='Official English joint text with named focal issuing parties; no equivalence to a separate national-language statement asserted')
            proof=dict(previous_hold='joint_signatory_attribution_review',criterion='Actual issuing-party/on-behalf-of formula names focal representatives, not inferred membership or attendance',source_url=d['canonical_url'],source_text_sha256=d['text_sha256'],proof_start=formula.start(),proof_end=formula.end(),proof_text=parties,method='Cached official government copy of original joint communication; shared event and split preserved')
            recovered.append(revised)
            ledger.append(dict(id='clearance-focus2-joint-'+digest(revised['candidate_id'].encode()),original_candidate_id=original['candidate_id'],replacement_candidate_id=revised['candidate_id'],original_holds=original['quality_flags'],clearances=[proof]+extra,remaining_holds=revised['quality_flags'],rejection=None,stance_judgment_changed=False,annotation_transferred=False,independent_human_check_asserted=False,training_approved=False))
    write_json(OUT/'joint_recovered_candidates.json',recovered)
    write_json(OUT/'joint_clearance_ledger.json',ledger)
    return dict(candidates=len(recovered),source_events=len({r['event_id'] for r in recovered}),primary_actors=sorted({r['actor_id'] for r in recovered}))

if __name__=='__main__':
    audit()
    audit_joint_parties()
