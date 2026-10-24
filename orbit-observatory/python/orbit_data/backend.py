"""Read-only local evidence API. Never writes public data or alignment scores."""
import argparse,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs,unquote
from .experimental_dataset import OUTPUT
from .validation import digest

ALLOWED_ORIGINS={'http://127.0.0.1:8000','http://localhost:8000'}


class EvidenceStore:
    def __init__(self,root=OUTPUT):
        self.root=root;manifest=json.loads((root/'dataset_manifest.json').read_text())
        for name,sha in manifest['files'].items():
            if digest((root/name).read_bytes())!=sha:raise ValueError('Frozen backend data changed: '+name)
        self.evidence=json.loads((root/'backend_evidence.json').read_text())
        groups=json.loads((root/'leakage_groups.json').read_text())
        held=set(groups['reserved_leakage_group_ids'])
        for row in self.evidence:
            if groups['event_groups'][row['event_id']] in held:raise ValueError('Reserved event in backend development evidence')
            if row['alignment_score'] is not None:raise ValueError('Experimental evidence cannot carry an alignment score')
        self.index={r['candidate_id']:r for r in self.evidence}
        self.report=json.loads((root/'experiment/experiment_report.json').read_text())
        if self.report['dataset_manifest_sha256']!=digest((root/'dataset_manifest.json').read_bytes()):raise ValueError('Experiment uses another dataset')
        self.predictions=json.loads((root/'experiment/experimental_predictions.json').read_text())
        expected=self.report['saved_artifacts']['experimental_predictions.json']
        if digest((root/'experiment/experimental_predictions.json').read_bytes())!=expected:raise ValueError('Prediction file changed')
        self.manifest_hash=digest((root/'dataset_manifest.json').read_bytes())
        for name,sha in self.report['saved_artifacts'].items():
            target=(root/'experiment'/name).resolve()
            if not target.is_relative_to((root/'experiment').resolve()) or digest(target.read_bytes())!=sha:raise ValueError('Experiment artifact changed')
        for pred in self.predictions:
            self.validate_prediction(pred)
        self.dataset_hash=manifest['files']['dataset.json']

    def validate_prediction(self,pred):
        from .experimental_baseline import validate_prediction
        validate_prediction(pred)
        if pred['dataset_manifest_sha256']!=self.manifest_hash:raise ValueError('Prediction dataset mismatch')
        row=self.index.get(pred['candidate_id'])
        if row is None or pred['event_id']!=row['event_id'] or pred['text_sha256']!=row['text_sha256'] or pred['lens_id']!=row['lens_id'] or pred['actor_id']!=row['actor_id']:raise ValueError('Prediction evidence mismatch')
        if pred['origin']!='trained_baseline_experiment' or pred['calibrated'] or pred['validated_for_publication'] or pred['alignment_score'] is not None:raise ValueError('Prediction is not safely marked experimental')
        if pred['split_role']!='development_validation_out_of_group':raise ValueError('Only out-of-group development predictions are exposed')
        if pred['model_id']+'.joblib' not in self.report['saved_artifacts'] or pred['model_id'].split('/')[0] not in self.report['trained_lenses']:raise ValueError('Prediction for an untrained lens')

    def query(self,path,query):
        base=dict(api_version='evidence-api-1.0.0',experimental=True,public_score_connection=False,dataset_sha256=self.dataset_hash)
        if path=='/api/status':
            return 200,dict(base,displayed_actors=['USA','EU','TUR','IND','ZAF'],auxiliary_actors=['RUS','UKR'],
                evidence_records=len(self.evidence),model_status='experimental_trained' if self.report['trained_lenses'] else 'not_trained_insufficient_data',
                trained_lenses=self.report['trained_lenses'],predictions=len(self.predictions),calibrated=False)
        if path=='/api/experimental-predictions':
            rows=self.predictions
            if query.get('lens'):rows=[r for r in rows if r['lens_id']==query['lens'][0]]
            return 200,dict(base,items=rows,total=len(rows),status='experimental_uncalibrated' if rows else 'no_predictions',alignment_score=None)
        if path=='/api/evidence':
            rows=self.evidence
            for param,key in [('actor','actor_id'),('lens','lens_id')]:
                if query.get(param):rows=[r for r in rows if r[key]==query[param][0]]
            if query.get('training_included'):rows=[r for r in rows if r['training_included']==(query['training_included'][0]=='true')]
            try:offset=int(query.get('offset',['0'])[0]);limit=int(query.get('limit',['25'])[0])
            except ValueError:return 400,dict(error='offset and limit must be integers')
            if offset<0 or not 1<=limit<=100:return 400,dict(error='offset must be nonnegative; limit must be 1-100')
            return 200,dict(base,items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit)
        if path.startswith('/api/evidence/'):
            row=self.index.get(unquote(path[len('/api/evidence/'):]))
            return (200,dict(base,evidence=row,experimental_predictions=[p for p in self.predictions if p['candidate_id']==row['candidate_id']])) if row else (404,dict(error='Unknown development evidence ID'))
        return 404,dict(error='Unknown API route')


def handler_class(store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            target=urlsplit(self.path)
            status,body=store.query(target.path,parse_qs(target.query))
            data=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)))
            origin=self.headers.get('Origin')
            if origin in ALLOWED_ORIGINS:self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
            self.end_headers();self.wfile.write(data)
        def log_message(self,*args):pass
    return Handler


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--dataset-root',type=__import__('pathlib').Path);args=parser.parse_args()
    from .experimental_baseline import active_dataset_root
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_class(EvidenceStore(args.dataset_root or active_dataset_root())))
    print(f'Local evidence API: http://127.0.0.1:{server.server_port}/api/status',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
