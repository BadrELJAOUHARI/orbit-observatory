"""Fixture checks or the frozen, per-lens experimental baseline pipeline."""
import argparse,json
from pathlib import Path
from .training import check_baseline_fixtures
from .validation import digest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',action='store_true')
    parser.add_argument('--approved-dataset',type=Path);parser.add_argument('--run-approved',action='store_true');parser.add_argument('--output',type=Path);parser.add_argument('--dataset-root',type=Path)
    args=parser.parse_args()
    if args.fixtures:
        if args.run_approved or args.approved_dataset:parser.error('Fixture and real-data modes must be separate')
        print(json.dumps(check_baseline_fixtures(),indent=2));return
    from .experimental_baseline import load_frozen,plan_lens,run,active_dataset_root
    from .experimental_dataset import OUTPUT
    from .validation import load_config
    root=args.dataset_root or active_dataset_root()
    rows,split,manifest=load_frozen(root)
    if args.run_approved:
        if args.approved_dataset is None:parser.error('--run-approved requires the frozen --approved-dataset')
        if digest(args.approved_dataset.read_bytes())!=manifest['files']['dataset.json']:raise ValueError('Use the evidence-gated frozen dataset, not an ad hoc edited label file')
        print(json.dumps(run(args.output,root),indent=2))
    else:print(json.dumps(dict(real_training_executed=False,eligible_rows=len(rows),lenses={lens:plan_lens([r for r in rows if r['lens_id']==lens]) for lens in load_config()[1]}),indent=2))

if __name__=='__main__':main()
