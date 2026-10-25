"""Check original-response reconstruction and preserved artifacts, without fitting."""
import json,subprocess,tempfile
from pathlib import Path
from collections import Counter
from .focal_retrieval import OUT,OLD,page
from .focal_review import PACKET
from .component_review import PACKET as COMPONENTS
from .validation import digest
from .text import normalize
from .collect import write_json

def verify():
    protected=json.loads((OUT/'protected_files.json').read_text())
    for p,h in protected.items():
        if digest(Path(p).read_bytes())!=h:raise ValueError('Protected prior artifact changed: '+p)
    docs=json.loads((OUT/'source_event_manifest.json').read_text());counts=Counter()
    for d in docs:
        raw=(OUT/d['source_receipt']['raw_path']).read_bytes()
        assert digest(raw)==d['source_receipt']['raw_sha256']
        # Reserved bodies are not interpreted in the verification/report pass.
        if d['event_role']=='evaluation_reserved':counts['reserved_receipt_hash_only']+=1;continue
        if d['source_type']=='wp':
            posts=json.loads(raw);post=next(x for x in posts if x['link'].rstrip('/')==d['canonical_url'].rstrip('/'));text=page(post['content']['rendered'].encode())[0]
        elif d['source_type']=='commission':text=page(json.loads(raw)['docuLanguageResource']['htmlContent'].encode())[0]
        elif d['source_type']=='council':
            with tempfile.TemporaryDirectory(prefix='orbit-source-check-',dir='/tmp') as tmp:
                p=Path(tmp)/'original.pdf';p.write_bytes(raw);text=normalize(subprocess.run(['pdftotext','-layout',str(p),'-'],check=True,capture_output=True,text=True).stdout)
        else:text=page(raw,'main' if d['source_type']=='govza' else None)[0]
        assert digest(text.encode())==d['text_sha256'],d['canonical_url']
        assert text==(OUT/d['text_path']).read_text()
        counts['reconstructed_'+d['source_type']]+=1
    for packet in [PACKET,COMPONENTS]:
        m=json.loads((packet/'manifest.json').read_text())
        for name,h in m['files'].items():assert digest((packet/name).read_bytes())==h
        refs=json.loads((packet/'source_refs.json').read_text())
        for r in refs.values():
            text=Path(r['source_text_path']).read_text();assert digest(text.encode())==r['text_sha256'];assert text[r['start']:r['end']]==r['exact_passage']
    prior={d['id']:d for d in json.loads((OLD/'source_event_manifest.json').read_text())};held={r['candidate_id']:r for r in json.loads((OLD/'held.json').read_text())}
    for c in json.loads((OUT/'held_clearance_ledger.json').read_text()):
        d=prior[held[c['original_candidate_id']]['document_id']];assert d['event_role']=='development_only';text=(OLD/d['text_path']).read_text()
        for proof in c['clearances']:assert text[proof['proof_start']:proof['proof_end']]==proof['proof_text']
        assert not c['annotation_transferred'] and not c['training_approved']
    report=dict(protected_prior_files_unchanged=len(protected),source_checks=dict(counts),original_response_reconstruction=True,clearance_proofs_reproduced=True,strict_and_component_packet_hashes_valid=True,reserved_body_interpretation=False)
    write_json(OUT/'verification.json',report);print(json.dumps(report,indent=2));return report

if __name__=='__main__':verify()
