"""Offline preparation and fail-closed training entry points. No automatic fitting."""
import json
import re
from collections import Counter
from .validation import ROOT

CONFIG=json.loads((ROOT/'configs/training-v2/pipeline.json').read_text())


def eligible_training_rows(rows, split):
    reserved=set(split['excluded_from_training_and_tuning_event_ids'])
    good=[]
    rejected=Counter()
    for row in rows:
        assisted=(row.get('origin')=='ai_assisted_reviewed' and row.get('schema_version')=='1.3.0'
            and row.get('review_status')=='reviewed_non_independent' and row.get('human_independent_check') is True
            and row.get('blind_independent_annotation') is False and row.get('independent_human') is False
            and row.get('ai_assisted') is True and bool(row.get('training_approval_id'))
            and row.get('training_policy_version')==CONFIG['pipeline_version'])
        authorized_assisted=(row.get('origin')=='ai_assisted_reviewed' and row.get('review_status')=='reviewed_non_independent'
            and row.get('training_policy_version')=='experimental-training-3.0.0' and row.get('record_scoped_authorization_verified') is True
            and bool(row.get('training_approval_id')) and row.get('ai_assisted') is True
            and row.get('blind_independent_annotation') is False and row.get('independent_human') is False)
        assisted=assisted or authorized_assisted
        human=(row.get('origin')=='human' and row.get('review_status') in CONFIG['approved_review_statuses'])
        if row['event_id'] in reserved or row.get('leakage_group_id') in set(split.get('reserved_leakage_group_ids',[])):reason='heldout_event_or_copy_group'
        elif not (assisted or human):reason='unapproved_label_provenance'
        elif row.get('training_approved') is not True:reason='no_training_approval'
        elif row.get('source_eligibility_cleared') is not True or row.get('text_quality_cleared') is not True:reason='source_or_text_hold'
        elif assisted and row.get('scope_cleared') is not True:reason='scope_hold'
        elif row.get('label') not in CONFIG['labels']:reason='excluded_supervised_target'
        else:
            good.append(row)
            continue
        rejected[reason]+=1
    return good,dict(rejected)


def prepare_training(rows,split):
    good,rejected=eligible_training_rows(rows,split)
    # Event hashing/grouping, never individual rows, controls the development split.
    events=sorted({r.get('leakage_group_id',r['event_id']) for r in good})
    from .validation import digest
    tune={e for e in events if int(digest(f"{CONFIG['seed']}:{e}".encode())[:8],16)%5==0}
    train=[r for r in good if r.get('leakage_group_id',r['event_id']) not in tune]
    validation=[r for r in good if r.get('leakage_group_id',r['event_id']) in tune]
    blockers=[]
    if not train:blockers.append('No approved source-cleared human training rows')
    if not validation:blockers.append('No disjoint development validation/calibration event group')
    if len({r['label'] for r in train})<2:blockers.append('Training requires at least two represented classes; do not invent opposition/mixed examples')
    return dict(status='blocked' if blockers else 'preflight_ready_not_trained',training_executed=False,
        train=train,validation=validation,rejected=rejected,blockers=blockers,
        heldout_event_ids=split['excluded_from_training_and_tuning_event_ids'],final_evaluation_ready=split['final_evaluation_ready'])


def assert_training_ready(prepared):
    if not prepared['train'] or not prepared['validation']:
        raise ValueError('Training blocked by missing approved event-disjoint data')
    train_events={r['event_id'] for r in prepared['train']}
    validation_events={r['event_id'] for r in prepared['validation']}
    heldout=set(prepared['heldout_event_ids'])
    train_groups={r.get('leakage_group_id',r['event_id']) for r in prepared['train']}
    validation_groups={r.get('leakage_group_id',r['event_id']) for r in prepared['validation']}
    if (train_groups|validation_groups)&set(prepared.get('heldout_leakage_group_ids',[])) or train_groups & validation_groups or train_events & validation_events or (train_events | validation_events) & heldout:
        raise ValueError('Event leakage')
    _,rejected=eligible_training_rows(prepared['train']+prepared['validation'],
        dict(excluded_from_training_and_tuning_event_ids=prepared['heldout_event_ids'],reserved_leakage_group_ids=prepared.get('heldout_leakage_group_ids',[])))
    if rejected:raise ValueError('Training data bypassed approval/eligibility guards')
    if len({r['label'] for r in prepared['train']})<2:
        raise ValueError('At least two genuine classes required')


def train_baseline(prepared):
    assert_training_ready(prepared)
    # Optional training dependencies are imported only after the data guards pass.
    pipeline=baseline_pipeline()
    pipeline.fit([r['proposition']+' [SEP] '+r['passage'] for r in prepared['train']],[r['label'] for r in prepared['train']])
    return pipeline


def baseline_pipeline():
    """Shared estimator construction, without data approval or fitting side effects."""
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    return make_pipeline(TfidfVectorizer(ngram_range=(1,2)),LogisticRegression(
        class_weight='balanced',max_iter=2000,random_state=CONFIG['seed']))


def check_baseline_fixtures():
    """Exercise fit/predict using explicitly artificial strings, never corpus evidence."""
    fixture=[]
    phrases={'support':'TEST_FIXTURE endorses measure', 'oppose':'TEST_FIXTURE rejects measure',
        'no_stance':'TEST_FIXTURE discusses unrelated subject', 'mixed':'TEST_FIXTURE endorses and rejects measure',
        'unresolved':'TEST_FIXTURE insufficient target scope'}
    for label,phrase in phrases.items():
        for number in range(4):
            fixture.append(dict(origin='test_fixture',event_id=f'TEST_ONLY_{label}_{number}',
                label=label,text=phrase+' synthetic example '+str(number)))
    train=[r for r in fixture if not r['event_id'].endswith('_3')]
    test=[r for r in fixture if r['event_id'].endswith('_3')]
    if {r['event_id'] for r in train}&{r['event_id'] for r in test}:raise ValueError('Fixture event overlap')
    model=baseline_pipeline();model.fit([r['text'] for r in train],[r['label'] for r in train])
    predictions=model.predict([r['text'] for r in test])
    if len(predictions)!=len(test) or not set(predictions)<=set(phrases):raise ValueError('Invalid baseline output')
    return dict(origin='test_fixture',train_events=len(train),test_events=len(test),
        classes=sorted(model.classes_.tolist()),fit_predict_passed=True,
        real_corpus_training_executed=False,real_world_performance_claim=False,
        model_checkpoint_saved=False,public_scores_changed=False)


def train_transformer(prepared,output_dir):
    revision=CONFIG['transformer']['revision']
    if not revision or not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('Pin a verified model commit before download')
    assert_training_ready(prepared)
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
    import torch
    labels=CONFIG['labels'];tokenizer=AutoTokenizer.from_pretrained(CONFIG['transformer']['model'],revision=revision)
    class EvidenceDataset(torch.utils.data.Dataset):
        def __init__(self,rows):self.rows=rows
        def __len__(self):return len(self.rows)
        def __getitem__(self,i):
            r=self.rows[i];tokens=tokenizer(r['proposition'],r['passage'],truncation=True,padding='max_length',max_length=512)
            return {**{k:torch.tensor(v) for k,v in tokens.items()},'labels':torch.tensor(labels.index(r['label']))}
    model=AutoModelForSequenceClassification.from_pretrained(CONFIG['transformer']['model'],revision=revision,num_labels=len(labels))
    args=TrainingArguments(output_dir=str(output_dir),seed=CONFIG['seed'],num_train_epochs=3,per_device_train_batch_size=4,
        per_device_eval_batch_size=4,report_to=[],save_strategy='epoch',eval_strategy='epoch')
    trainer=Trainer(model=model,args=args,train_dataset=EvidenceDataset(prepared['train']),eval_dataset=EvidenceDataset(prepared['validation']))
    trainer.train();trainer.save_model();tokenizer.save_pretrained(str(output_dir))


def main():
    frozen=ROOT.parent/'.local/experimental-baseline-v1/dataset_manifest.json'
    if frozen.exists():
        from .experimental_baseline import load_frozen,plan_lens,active_dataset_root
        from .validation import load_config
        rows,split,manifest=load_frozen(active_dataset_root())
        print(json.dumps(dict(policy_version=manifest.get('policy_version',CONFIG['pipeline_version']),training_executed=False,
            eligible_rows=len(rows),lenses={lens:plan_lens([r for r in rows if r['lens_id']==lens]) for lens in load_config()[1]}),indent=2))
        return
    from .workflow import load_corpus
    records,*_=load_corpus()
    index={r['id']:r for r in records}
    extra=ROOT.parent/'.local/expansion-v6/candidates.json'
    if extra.exists():index.update({c['id']:c for c in json.loads(extra.read_text())})
    for path in sorted((ROOT.parent/'.local/workflow-returns').glob('*/annotations.json')):
        records+=json.loads(path.read_text())
    rows=[dict(r,event_id=index[r['claim_id']]['event_id']) for r in records if r['record_type']=='annotation']
    split=json.loads((ROOT/'workflow/v1/event_split.json').read_text())
    if extra.exists():
        from .expansion import event_roles
        split=dict(split,excluded_from_training_and_tuning_event_ids=sorted(set(split['excluded_from_training_and_tuning_event_ids'])|{e for e,r in event_roles().items() if r=='evaluation_reserved'}))
    prepared=prepare_training(rows,split)
    print(json.dumps({k:v for k,v in prepared.items() if k not in ('train','validation')},indent=2))

if __name__=='__main__':main()
