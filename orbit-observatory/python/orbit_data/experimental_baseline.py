"""Per-lens event-group validation; skip only the lenses that fail data gates."""
import argparse,json,platform
from collections import Counter,defaultdict
from pathlib import Path
from .validation import ROOT,digest,load_config
from .experimental_dataset import OUTPUT,POLICY
from .reviewed import write_immutable
from .training import train_baseline


def validate_prediction(pred):
    from jsonschema import Draft202012Validator
    schema=json.loads((ROOT/'schemas/experimental-v1/prediction.schema.json').read_text())
    Draft202012Validator(schema).validate(pred)
    import math
    if not all(math.isfinite(value) for value in pred['probabilities'].values()) or abs(sum(pred['probabilities'].values())-1)>1e-8 or pred['predicted_label'] not in pred['probabilities']:
        raise ValueError('Invalid experimental class probabilities')


def plan_lens(rows):
    classes=sorted({r['label'] for r in rows});groups=sorted({r['leakage_group_id'] for r in rows})
    class_groups={label:sorted({r['leakage_group_id'] for r in rows if r['label']==label}) for label in classes}
    reasons=[]
    if len(groups)<2:reasons.append(f'Need at least two disjoint event groups; found {len(groups)}')
    if len(classes)<2:reasons.append(f'Need at least two represented supervised classes; found {classes}')
    for label,ids in class_groups.items():
        if len(ids)<2:reasons.append(f'{label} occurs in only {len(ids)} event group; leaving it out removes that class from training')
    folds=[]
    for group in groups:
        train=[r for r in rows if r['leakage_group_id']!=group];val=[r for r in rows if r['leakage_group_id']==group]
        fold=dict(validation_group=group,train_candidate_ids=[r['candidate_id'] for r in train],validation_candidate_ids=[r['candidate_id'] for r in val],
            train_events=sorted({r['event_id'] for r in train}),validation_events=sorted({r['event_id'] for r in val}),train_class_counts=dict(Counter(r['label'] for r in train)),validation_class_counts=dict(Counter(r['label'] for r in val)))
        if len({r['label'] for r in train})<2:fold['blocked']='Training fold has fewer than two classes'
        folds.append(fold)
    return dict(rows=len(rows),events=len({r['event_id'] for r in rows}),groups=len(groups),represented_classes=classes,
        missing_classes=sorted(set(['support','oppose','no_stance','mixed'])-set(classes)),class_counts=dict(Counter(r['label'] for r in rows)),
        class_event_groups={label:len(ids) for label,ids in class_groups.items()},eligible_to_run=not reasons,reasons=reasons,folds=folds)


def load_frozen(root=None):
    root=root or OUTPUT
    manifest=json.loads((root/'dataset_manifest.json').read_text())
    for name,sha in manifest['files'].items():
        if digest((root/name).read_bytes())!=sha:raise ValueError('Frozen dataset artifact changed: '+name)
    policy=(ROOT/'configs/training-v3/pipeline.json') if manifest.get('policy_version')=='experimental-training-3.0.0' else POLICY
    if digest(policy.read_bytes())!=manifest['policy_sha256']:raise ValueError('Training policy changed after freezing')
    rows=json.loads((root/'dataset.json').read_text())
    from .experimental_dataset import validate_training_view
    from .authorized_dataset import validate_view
    for row in rows:
        (validate_view if row.get('record_type')=='experimental_training_example' else validate_training_view)(row)
    if manifest.get('policy_version')=='experimental-training-3.0.0':
        grant=json.loads((root/'training_authorization.json').read_text())
        authorized={e['candidate_id']:e for e in grant['records']}
        for row in rows:
            entry=authorized.get(row['candidate_id'])
            if not entry or not entry['supervised_training_approved'] or entry['annotation_id']!=row['annotation_id'] or entry['existing_human_independent_check']!=row['human_independent_check']:
                raise ValueError('Training row exceeds record-scoped authorization')
    return rows,json.loads((root/'training_split.json').read_text()),manifest


def run(destination=None,dataset_root=None):
    root=dataset_root or OUTPUT
    rows,split,manifest=load_frozen(root) if dataset_root else load_frozen();destination=destination or root/'experiment'
    snapshot=digest((root/'dataset_manifest.json').read_bytes())
    report_path=destination/'experiment_report.json'
    if report_path.exists():
        report=json.loads(report_path.read_text())
        if report['dataset_manifest_sha256']!=snapshot:raise ValueError('Cannot replace prior experiment with different data')
        for name,sha in report['saved_artifacts'].items():
            if digest((destination/name).read_bytes())!=sha:raise ValueError('Experiment artifact hash mismatch')
        return report
    plans={lens:plan_lens([r for r in rows if r['lens_id']==lens]) for lens in load_config()[1]}
    predictions=[];artifacts={};trained=[]
    for lens,plan in plans.items():
        if not plan['eligible_to_run']:
            plan.update(status='skipped_insufficient_data',validation_metrics=None,model_path=None);continue
        import joblib
        from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
        selected=[r for r in rows if r['lens_id']==lens];truth=[];labels=[];weights=[];majority_labels=[];event_outcomes=defaultdict(list);majority_events=defaultdict(list)
        for number,fold in enumerate(plan['folds']):
            group=fold['validation_group'];train=[r for r in selected if r['leakage_group_id']!=group];val=[r for r in selected if r['leakage_group_id']==group]
            prepared=dict(train=train,validation=val,heldout_event_ids=split['excluded_from_training_and_tuning_event_ids'],heldout_leakage_group_ids=split['reserved_leakage_group_ids'])
            model=train_baseline(prepared)
            lensdir=destination/lens;lensdir.mkdir(parents=True,exist_ok=True)
            path=lensdir/f'fold-{number}.joblib';joblib.dump(model,path);artifacts[str(path.relative_to(destination))]=digest(path.read_bytes())
            inputs=[r['proposition']+' [SEP] '+r['passage'] for r in val];out=model.predict(inputs);probs=model.predict_proba(inputs)
            populations=Counter(r['event_id'] for r in val)
            train_counts=Counter(r['label'] for r in train)
            majority=min(train_counts,key=lambda label:(-train_counts[label],label))
            fold.update(model_accuracy=float(accuracy_score([r['label'] for r in val],out)),majority_label=majority,majority_accuracy=float(accuracy_score([r['label'] for r in val],[majority]*len(val))),train_rows=len(train),validation_rows=len(val))
            for row,label,prob in zip(val,out,probs):
                truth.append(row['label']);labels.append(str(label));majority_labels.append(majority);majority_events[row['event_id']].append(majority==row['label']);weights.append(1/populations[row['event_id']]);event_outcomes[row['event_id']].append(str(label)==row['label'])
                predictions.append(dict(record_type='experimental_prediction',schema_version='1.0.0',origin='trained_baseline_experiment',candidate_id=row['candidate_id'],
                    event_id=row['event_id'],actor_id=row['actor_id'],actor_role=row['actor_role'],lens_id=lens,text_sha256=row['text_sha256'],
                    predicted_label=str(label),probabilities={str(k):float(v) for k,v in zip(model.classes_,prob)},
                    model_id=lens+'/fold-'+str(number),dataset_manifest_sha256=snapshot,split_role='development_validation_out_of_group',
                    calibrated=False,validated_for_publication=False,alignment_score=None,review_status='machine_unreviewed'))
        # Save an experimental final fit on all eligible development groups after OOF validation.
        # Reuse the exact validated baseline estimator construction for a final fit.
        from .training import baseline_pipeline
        final=baseline_pipeline();final.fit([r['proposition']+' [SEP] '+r['passage'] for r in selected],[r['label'] for r in selected])
        path=destination/lens/'final.joblib';joblib.dump(final,path);artifacts[str(path.relative_to(destination))]=digest(path.read_bytes())
        order=plan['represented_classes']
        plan.update(status='trained_experimental',model_path=str(path.relative_to(destination)),validation_metrics=dict(
            claim_accuracy=accuracy_score(truth,labels),macro_f1_represented_classes=f1_score(truth,labels,labels=order,average='macro',zero_division=0),
            event_weighted_accuracy=accuracy_score(truth,labels,sample_weight=weights),
            event_weighted_confusion_matrix=confusion_matrix(truth,labels,labels=order,sample_weight=weights).tolist(),class_order=order,
            per_event_accuracy={e:sum(values)/len(values) for e,values in event_outcomes.items()}))
        plan['majority_comparator']=dict(method='Most frequent class in each training fold only; lexical tie break, no held-out label use',
            claim_accuracy=accuracy_score(truth,majority_labels),macro_f1_represented_classes=f1_score(truth,majority_labels,labels=order,average='macro',zero_division=0),
            event_weighted_accuracy=accuracy_score(truth,majority_labels,sample_weight=weights),per_event_accuracy={e:sum(v)/len(v) for e,v in majority_events.items()})
        trained.append(lens)
    for pred in predictions:validate_prediction(pred)
    write_immutable(destination/'experimental_predictions.json',predictions)
    artifacts['experimental_predictions.json']=digest((destination/'experimental_predictions.json').read_bytes())
    import sklearn,numpy
    report=dict(version='experimental-baseline-1.0.0',dataset_manifest_sha256=snapshot,dataset_sha256=manifest['files']['dataset.json'],policy_version=manifest.get('policy_version','experimental-training-2.0.0'),
        actual_eligible_rows=len(rows),actual_eligible_events=len({r['event_id'] for r in rows}),actual_eligible_groups=len({r['leakage_group_id'] for r in rows}),
        class_counts=dict(Counter(r['label'] for r in rows)),trained_lenses=trained,real_data_training_executed=bool(trained),lenses=plans,
        validation='Leave one connected communication-event group out; fixed preprocessing and hyperparameters; reserved evaluation never fitted, predicted or tuned.',
        reserved_evaluation_used=False,calibrated=False,public_scores_changed=False,alignment_scores_produced=False,
        annotation_origin='ai_assisted_reviewed',human_independent_check=True if all(r.get('human_independent_check') is True for r in rows) else None,
        human_check_provenance_counts=dict(Counter('explicit_check' if r.get('human_independent_check') is True else 'not_newly_asserted' for r in rows)),blind_independent_annotation=False,
        runtime=dict(python=platform.python_version(),sklearn=sklearn.__version__,numpy=numpy.__version__),saved_artifacts=artifacts,
        limitations=['Small purposive development sample; no representative country-period estimate.',
            'Human-checked assisted annotations are not blind independent evaluation gold.',
            'Unresolved, source/text/attribution/scope-held items excluded; missing classes not fabricated.',
            'No validation score or model is produced for skipped lenses. No pooled rescue across different targets.'])
    write_immutable(report_path,report);return report


def active_dataset_root():
    pointer=ROOT/'workflow/experimental-baseline-v2/active.json'
    if not pointer.exists():return OUTPUT
    record=json.loads(pointer.read_text());root=(ROOT/record['dataset_root']).resolve()
    if digest((root/'dataset_manifest.json').read_bytes())!=record['dataset_manifest_sha256']:raise ValueError('Active dataset pointer checksum mismatch')
    return root


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--dataset-root',type=Path);args=parser.parse_args()
    report=run(args.output,args.dataset_root or active_dataset_root())
    print(json.dumps(dict(eligible_rows=report['actual_eligible_rows'],eligible_events=report['actual_eligible_events'],trained_lenses=report['trained_lenses'],
        lenses={lens:dict(rows=p['rows'],status=p['status'],reasons=p['reasons']) for lens,p in report['lenses'].items()}),indent=2))

if __name__=='__main__':main()
