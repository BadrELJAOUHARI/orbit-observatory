"""Freeze human-verified assisted development labels behind unchanged evidence gates."""
import json,re,itertools
from collections import Counter,defaultdict
from difflib import SequenceMatcher
from .validation import ROOT,digest,validate_record,load_config
from .expansion import OUT as CORPUS,event_roles,validate_expansion
from .reviewed import write_immutable
from .training import eligible_training_rows

OUTPUT=ROOT.parent/'.local/experimental-baseline-v1'
REVIEW=ROOT.parent/'.local/workflow-returns/Badr_A-expanded-0002'
POLICY=ROOT/'configs/training-v2/pipeline.json'


def leakage_groups(documents,claims,reserved):
    parent={};edges=[]
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    def union(a,b,why,details=None):
        a0,b0=a,b;a,b=find(a),find(b)
        if a!=b:
            parent[max(a,b)]=min(a,b)
            edges.append(dict(event_a=a0,event_b=b0,relation=why,details=details))
    docs={d.get('document_id',d.get('id')):d for d in documents}
    shared={}
    for d in docs.values():
        event=d['event_id'];find(event)
        for relation in ('duplicate_of','translation_of'):
            if d.get(relation) in docs:union(event,docs[d[relation]]['event_id'],relation)
        for key in ('text_sha256','joint_statement_id','duplicate_cluster_id'):
            value=d.get(key)
            if value:
                if (key,value) in shared:union(event,shared[key,value],key)
                else:shared[key,value]=event
    for c in claims:find(c['event_id'])
    # Detect substantial copied/overlapping passages across documents/events.
    # No labels enter this step; generic short diplomatic formulas are excluded.
    shingles=defaultdict(list);tokens={};pairs=set()
    for i,c in enumerate(claims):
        words=re.findall(r'\w+',c.get('reading_text',c.get('exact_passage',c.get('quote',''))).casefold())
        if len(words)<12:continue
        tokens[i]=words
        for part in set(tuple(words[n:n+12]) for n in range(len(words)-11)):
            for j in shingles[part]:
                if claims[j]['event_id']!=c['event_id']:pairs.add((min(i,j),max(i,j)))
            shingles[part].append(i)
    for i,j in sorted(pairs):
        a,b=tokens[i],tokens[j];size=SequenceMatcher(None,a,b,autojunk=False).find_longest_match().size
        if size/min(len(a),len(b))>=.8:
            union(claims[i]['event_id'],claims[j]['event_id'],'substantial_passage_overlap',dict(candidate_a=claims[i]['id'],candidate_b=claims[j]['id'],matching_tokens=size,shorter_tokens=min(len(a),len(b))))
    for event in reserved:find(event)
    clusters=defaultdict(list)
    for event in sorted(parent):clusters[find(event)].append(event)
    mapping={e:'leakage-'+digest('|'.join(es).encode()) for es in clusters.values() for e in es}
    reserved_groups=sorted({mapping[e] for e in reserved})
    return dict(event_groups=mapping,reserved_event_ids=sorted(reserved),reserved_leakage_group_ids=reserved_groups,edges=edges,
        method='Whole events, known mirrors/translations/joint links, document hashes; cross-event exact token overlap >=12 tokens and >=80% of shorter passage. No labels used.')


def evidence_reasons(row,annotation,reserved,group_id,reserved_groups):
    reasons=[]
    if row['event_id'] in reserved or group_id in reserved_groups:reasons.append('reserved_event_or_related_group')
    assisted=(annotation.get('schema_version')=='1.3.0' and annotation.get('human_independent_check') is True and annotation.get('ai_assisted') is True and annotation.get('origin')=='ai_assisted_reviewed' and annotation.get('training_approved') is True)
    if not assisted:reasons.append('not_in_record_scoped_training_approval')
    flags=[x for x in row['quality_flags'].split(';') if x]
    if row['quarantine']=='true' or flags:reasons.append('existing_source_or_text_hold')
    reasons.extend('hold:'+x for x in flags)
    # Approval is distinct from the returned evidence checks, never a defect waiver.
    if row['human_source_eligibility']!='eligible':reasons.append('source_not_cleared')
    if row['human_text_quality']!='usable':reasons.append('text_not_cleared')
    if row['human_attribution']!='attributable':reasons.append('attribution_not_cleared')
    label=annotation['label']
    if label in ('unresolved','not_applicable'):reasons.append('excluded_supervised_target:'+label)
    expected_scope='no_relevant_stance' if label=='no_stance' else 'exact_target_met'
    if row['human_scope']!=expected_scope:reasons.append('strict_scope_not_met')
    if any('scope' in f or 'W1' in f for f in flags):reasons.append('preserved_scope_or_W1_hold')
    return reasons


def counts(rows):
    return dict(rows=len(rows),events=len({r['event_id'] for r in rows}),groups=len({r['leakage_group_id'] for r in rows}),
        by_lens={lens:dict(rows=sum(r['lens_id']==lens for r in rows),
            classes=dict(Counter(r['label'] for r in rows if r['lens_id']==lens)),
            events=len({r['event_id'] for r in rows if r['lens_id']==lens}),
            groups=len({r['leakage_group_id'] for r in rows if r['lens_id']==lens})) for lens in load_config()[1]})


def validate_training_view(row):
    from jsonschema import Draft202012Validator,FormatChecker
    schema=json.loads((ROOT/'schemas/experimental-v1/training_view.schema.json').read_text())
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(row)
    if row['candidate_id']!=row['claim_id'] or row['end']-row['start']!=len(row['passage']):raise ValueError('Training feature reference/offset mismatch')
    if row['proposition']!=load_config()[1][row['lens_id']]['definition']:raise ValueError('Training proposition changed')


def build():
    from .workflow import load_corpus
    records,candidates,index,texts,*_=load_corpus()
    docs=[r for r in records if r['record_type']=='document']
    new_docs=json.loads((CORPUS/'cleared_catalog.json').read_text());new_claims=json.loads((CORPUS/'candidates.json').read_text())
    validate_expansion(new_docs,new_claims,event_roles())
    all_claims=[r for r in records if r['record_type']=='claim']+new_claims
    split=json.loads((ROOT/'workflow/v1/event_split.json').read_text())
    reserved=set(split['excluded_from_training_and_tuning_event_ids'])|{e for e,role in event_roles().items() if role=='evaluation_reserved'}
    groups=leakage_groups(docs+new_docs,all_claims,reserved)
    annotations=json.loads((REVIEW/'annotations.json').read_text())
    ledger=json.loads((REVIEW/'ledger.json').read_text())
    if digest((REVIEW/'submitted.csv').read_bytes())!=ledger['submission_sha256'] or digest((REVIEW/'submitted_approval.json').read_bytes())!=ledger['approval_sha256']:raise ValueError('Submitted approval/CSV hash mismatch')
    for a in annotations:validate_record(a)
    anns={a['claim_id']:a for a in annotations}
    legacy=json.loads((ROOT.parent/'.local/workflow-returns/Badr_A-development-0001/annotations.json').read_text())
    legacy={a['claim_id']:a for a in legacy}
    returned=json.loads((REVIEW/'returned_rows.json').read_text())
    baseline=json.loads((ROOT.parent/'.local/development-review-expanded-v2-20261023/review_queue.json').read_text())
    frozen=[];decisions=[];evidence=[]
    for source,row in zip(baseline,returned):
        if source['candidate_id']!=row['candidate_id']:raise ValueError('Baseline order changed')
        new=row['candidate_id'] in anns;a=anns.get(row['candidate_id'],legacy.get(row['candidate_id']))
        if not a:raise ValueError('Missing preserved prior annotation')
        gid=groups['event_groups'][row['event_id']]
        reasons=evidence_reasons(row,a,reserved,gid,set(groups['reserved_leakage_group_ids'])) if new else ['not_in_record_scoped_training_approval']
        decision=dict(candidate_id=row['candidate_id'],annotation_id=a['id'],actor_id=row['actor_id'],lens_id=row['lens_id'],event_id=row['event_id'],leakage_group_id=gid,
            label=a['label'],training_approved=a.get('training_approved',False),human_independent_check=a.get('human_independent_check',False),
            origin=a['origin'],blind_independent_annotation=False,included=not reasons,reasons=reasons,existing_quality_flags=source['quality_flags'])
        decisions.append(decision)
        if gid not in groups['reserved_leakage_group_ids']:
            evidence.append(dict(candidate_id=row['candidate_id'],event_id=row['event_id'],document_id=row['document_id'],actor_id=row['actor_id'],actor_role=row['actor_role'],
                event_date=row['event_date'],lens_id=row['lens_id'],proposition=row['lens_proposition'],source_url=row['source_url'],issuer=row['document_issuer'],
                language=row['language'],text_sha256=row['text_sha256'],start=int(row['start']),end=int(row['end']),exact_passage=row['exact_passage'],
                reading_text=row['reading_text'],context_before=row['context_before'],context_after=row['context_after'],quality_flags=source['quality_flags'],
                quarantine=source['quarantine']=='true',human_annotation=a,training_included=not reasons,exclusion_reasons=reasons,alignment_score=None))
        if reasons:continue
        frozen.append(dict(**a,candidate_id=row['candidate_id'],event_id=row['event_id'],document_id=row['document_id'],actor_id=row['actor_id'],actor_role=row['actor_role'],
            lens_id=row['lens_id'],event_date=row['event_date'],language=row['language'],proposition=row['lens_proposition'],passage=row['exact_passage'],
            reading_text=row['reading_text'],text_sha256=row['text_sha256'],start=int(row['start']),end=int(row['end']),source_url=row['source_url'],
            leakage_group_id=gid,source_eligibility_cleared=True,text_quality_cleared=True,scope_cleared=True,alignment_score=None))
    train_split=dict(excluded_from_training_and_tuning_event_ids=sorted(reserved),reserved_leakage_group_ids=groups['reserved_leakage_group_ids'],final_evaluation_ready=False)
    for row in frozen:validate_training_view(row)
    accepted,rejected=eligible_training_rows(frozen,train_split)
    if rejected or len(accepted)!=len(frozen):raise ValueError('Freeze bypassed training provenance gates')
    payloads={'dataset.json':frozen,'inclusion_exclusion_ledger.json':decisions,'leakage_groups.json':groups,'training_split.json':train_split,'backend_evidence.json':evidence,
        'counts.json':dict(approved_new_annotations=len(annotations),legacy_annotations_preserved=len(legacy),approved_label_counts=dict(Counter(a['label'] for a in annotations)),
            eligible=counts(frozen),primary_exclusion_counts=dict(Counter(d['reasons'][0] for d in decisions if d['reasons'])),
            all_exclusion_counts=dict(Counter(reason for d in decisions for reason in d['reasons'])),
            experimental_only=True,blind_independent_annotation_count=0,public_scores_changed=False)}
    for name,value in payloads.items():write_immutable(OUTPUT/name,value)
    preprocessing=dict(policy_version='experimental-training-2.0.0',features='word TF-IDF',ngram_range=[1,2],lowercase=True,classifier='logistic_regression',class_weight='balanced',max_iter=2000,random_state=20261023,input='proposition + [SEP] + exact stored passage',labels=['support','oppose','no_stance','mixed'],calibrated=False,alignment_scores_produced=False)
    write_immutable(OUTPUT/'preprocessing.json',preprocessing)
    manifest=dict(version='experimental-dataset-1.0.0',review_id='Badr_A-expanded-0002',submission_sha256=ledger['submission_sha256'],approval_sha256=ledger['approval_sha256'],
        policy_sha256=digest(POLICY.read_bytes()),files={name:digest((OUTPUT/name).read_bytes()) for name in list(payloads)+['preprocessing.json']},
        reserved_events_used=False,annotation_origin='ai_assisted_reviewed',human_independent_check=True,blind_independent_annotation=False,
        W1_preserved=True,unresolved_excluded=True,no_stance_alignment_score=None)
    write_immutable(OUTPUT/'dataset_manifest.json',manifest)
    print(json.dumps(payloads['counts.json'],indent=2));return manifest

if __name__=='__main__':build()
