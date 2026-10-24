"""Synthetic fixtures only. No network requests or research labels in these tests."""

import copy
import io
import json
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jsonschema import ValidationError

from orbit_data.collect import Downloader, build_records, collect, extract, utcnow
from orbit_data.text import candidate_spans, html_text, normalize
from orbit_data.validation import ROOT, digest, validate_dataset, validate_manifest, validate_record


class SyntheticDownloader:
    def __init__(self, output):
        self.output = output

    def download(self, url):
        # These are synthetic paragraphs, not purported official quotations.
        raw = ('<html><main><p>SYNTHETIC fixture: Ukraine sovereignty café.</p><p>Troops withdraw.</p>'
               '<p>This paragraph supplies synthetic context for testing only. It is not an official source, '
               'a human annotation, or a model result. It intentionally contains enough text to pass the '
               'error-page length guard while keeping the test independent of external services.</p></main></html>').encode()
        path = 'raw/' + digest(raw) + '.bin'
        (self.output / 'raw').mkdir(exist_ok=True)
        (self.output / path).write_bytes(raw)
        return raw, dict(resolved_url=url, retrieved_at='2026-10-23T00:00:00Z', content_type='text/html', raw_path=path, raw_sha256=digest(raw))


def fixture_manifest():
    manifest = json.loads((ROOT / 'source_manifest/v1/pilot.json').read_text())
    entry = copy.deepcopy(manifest['sources'][2])
    entry['id'] = 'synthetic-doc-a'
    entry['event_id'] = 'synthetic-event-a'
    entry['url'] = 'https://www.consilium.europa.eu/synthetic-fixture-a'
    entry['identity_markers'] = [['SYNTHETIC']]
    entry['extraction'] = dict(kind='html', root='main', encoding='utf-8')
    manifest['sources'] = [entry]
    return manifest


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.manifest = fixture_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def build(self, manifest=None):
        return build_records(manifest or self.manifest, self.output, SyntheticDownloader(self.output))[0]

    def test_all_actor_lens_contracts_and_real_manifest(self):
        entries = validate_manifest(json.loads((ROOT / 'source_manifest/v1/pilot.json').read_text()))
        self.assertEqual(len(entries), 10)
        from collections import Counter
        self.assertEqual(set(Counter(e['actor_id'] for e in entries.values()).values()), {2})
        from orbit_data.validation import load_config, SCHEMA
        actors,lenses=load_config()
        self.assertEqual(set(actors), {'USA','EU','TUR','IND','ZAF'})
        self.assertEqual(len(lenses),5)
        self.assertEqual(lenses['invasion_responsibility']['applicable_from'],'2022-02-24')
        self.assertEqual(set(SCHEMA['$defs']['claim']['properties']['lens_id']['enum']),set(lenses))

    def test_unicode_normalization_and_exact_offsets(self):
        text = normalize('Cafe\u0301\u00a0 Ukraine\r\n\r\nSecond\tline')
        self.assertEqual(text, 'Café Ukraine\nSecond line')
        for start, end, quote in candidate_spans(text, ['Ukraine', 'line']):
            self.assertEqual(text[start:end], quote)

    def test_navigation_removed_and_missing_root_rejected(self):
        text, _ = html_text(b'<main><nav>ignore</nav><p>Keep</p><script>bad</script></main>', {'root':'main'})
        self.assertEqual(text, 'Keep')
        with self.assertRaises(ValueError):
            html_text(b'<body>error page</body>', {'root':'main'})

    def test_pdf_resolution_uses_attachment_language_not_page_or_summary(self):
        entry=copy.deepcopy(self.manifest['sources'][0])
        entry.update(url='https://gadebate.un.org/en/77/synthetic',extraction={'kind':'un_statement_pdf'},language='fr')
        html=b'<p>Statement</p><p>European Union</p><a hreflang="fr" href="/fr/77/synthetic">French page</a><a href="/files/test_en.pdf">English</a><a href="/files/test_fr.pdf">French</a>'
        raw=b'%PDF-SYNTHETIC-FIXTURE'
        downloader=SimpleNamespace(download=lambda url:(html if url==entry['url'] else raw,{'resolved_url':url,'content_type':'text/html'}))
        page=SimpleNamespace(extract_text=lambda:'SYNTHETIC French-language attachment fixture. '*10)
        with patch('orbit_data.collect.PdfReader',return_value=SimpleNamespace(pages=[page])):
            text,meta,canonical=extract(entry,downloader)
        self.assertTrue(meta['resolved_url'].endswith('test_fr.pdf'))
        self.assertIn('SYNTHETIC',text)
        self.assertEqual(canonical,entry['url'])

    def test_evidence_integrity_and_hash_tampering(self):
        records = self.build()
        validate_dataset(records, self.output)
        claim = next(r for r in records if r['record_type'] == 'claim')
        claim['end'] -= 1
        with self.assertRaisesRegex(ValueError, 'offsets'):
            validate_dataset(records, self.output)
        records = self.build()
        doc = next(r for r in records if r['record_type'] == 'document')
        (self.output / doc['text_path']).write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'hash'):
            validate_dataset(records, self.output)

    def test_exact_copy_preserves_link_without_duplicate_claims(self):
        baseline = self.build()
        copy_entry = copy.deepcopy(self.manifest['sources'][0])
        copy_entry['id'] = 'synthetic-doc-b'
        copy_entry['url'] += '-copy'
        self.manifest['sources'].append(copy_entry)
        records = self.build()
        docs = [r for r in records if r['record_type'] == 'document']
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[1]['duplicate_of'], docs[0]['id'])
        self.assertEqual(sum(r['record_type']=='claim' for r in records), sum(r['record_type']=='claim' for r in baseline))
        self.assertEqual(sum(r['record_type']=='event' for r in records), 1)

    def test_translation_stays_in_same_event(self):
        entry = copy.deepcopy(self.manifest['sources'][0])
        entry.update(id='synthetic-translation', language='fr', translation_of='synthetic-doc-a', translation_provenance='Synthetic test-only official translation linkage')
        self.manifest['sources'].append(entry)
        records = self.build()
        doc = next(r for r in records if r['id'] == 'synthetic-translation')
        self.assertEqual(doc['translation_of'], 'synthetic-doc-a')
        self.assertFalse(any(r.get('document_id') == doc['id'] for r in records))

    def test_repeated_text_on_new_date_remains_new_event(self):
        entry = copy.deepcopy(self.manifest['sources'][0])
        entry.update(id='synthetic-doc-b', event_id='synthetic-event-b', event_date='2022-02-25', delivery_date='2022-02-25')
        self.manifest['sources'].append(entry)
        records = self.build()
        self.assertEqual(sum(r['record_type']=='event' for r in records), 2)
        self.assertFalse(any(r.get('duplicate_of') for r in records))

    def test_pre_invasion_responsibility_not_generated(self):
        entry = self.manifest['sources'][0]
        entry.update(event_date='2014-03-12', delivery_date='2014-03-12')
        self.assertFalse(any(r.get('lens_id')=='invasion_responsibility' for r in self.build()))

    def test_missing_provenance_and_prediction_label_mixing_rejected(self):
        doc = next(r for r in self.build() if r['record_type']=='document')
        del doc['retrieved_at']
        with self.assertRaises(ValidationError): validate_record(doc)
        annotation = dict(schema_version='1.0.0',record_type='annotation',id='synthetic-annotation',claim_id='synthetic-claim',origin='human',annotator_id='test-only',codebook_version='test-v1',label='support',review_status='independent',created_at=utcnow(),rationale='Synthetic test only',supersedes=None)
        validate_record(annotation)
        annotation['origin']='model'
        with self.assertRaises(ValidationError): validate_record(annotation)
        prediction = dict(schema_version='1.0.0',record_type='prediction',id='synthetic-prediction',claim_id='synthetic-claim',origin='model',model_version='test-v1',training_data_version='test-data',calibration_version=None,calibrated=False,created_at=utcnow(),eligibility='stance_bearing',support_probability=.8,stance_score=.6)
        validate_record(prediction)
        prediction['calibrated']=True
        with self.assertRaises(ValidationError): validate_record(prediction)
        prediction.update(calibrated=False,stance_score=.5)
        with self.assertRaises(ValueError): validate_record(prediction)

    def test_manifest_conflicts_and_dangling_links_rejected(self):
        self.manifest['sources'].append(copy.deepcopy(self.manifest['sources'][0]))
        with self.assertRaises(ValueError): validate_manifest(self.manifest)
        self.manifest = fixture_manifest()
        records = self.build()
        records.append(copy.deepcopy(records[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate record'): validate_dataset(records,self.output)
        records = self.build()
        next(r for r in records if r['record_type']=='claim')['event_id']='missing'
        with self.assertRaises(KeyError): validate_dataset(records,self.output)

    def test_cached_download_is_reused_and_checksum_checked(self):
        class Response(io.BytesIO):
            url='https://www.consilium.europa.eu/synthetic-fixture'
            from email.message import Message
            headers=Message()
            headers['Content-Type']='text/html'
        downloader = Downloader(self.output, {'www.consilium.europa.eu'}, interval=0)
        with patch.object(downloader.opener,'open',return_value=Response(b'synthetic')) as request:
            raw, meta=downloader.fetch(Response.url)
            self.assertEqual(downloader.fetch(Response.url)[0],raw)
            self.assertEqual(request.call_count,1)
        (self.output/meta['raw_path']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'checksum'): downloader.fetch(Response.url)

    def test_robots_404_cached_and_denial_not_bypassed(self):
        downloader=Downloader(self.output,{'www.consilium.europa.eu'},interval=0)
        url='https://www.consilium.europa.eu/synthetic-fixture'
        error=urllib.error.HTTPError(url,404,'Not Found',{},None)
        with patch.object(downloader.opener,'open',side_effect=error) as request:
            downloader.check_robots(url)
            downloader.check_robots(url)
            self.assertEqual(request.call_count,1)
        other='https://www.consilium.europa.eu/robots.txt'
        (self.output/'cache'/(digest(other.encode())+'.json')).unlink()
        with patch.object(downloader.opener,'open',side_effect=urllib.error.URLError('Tunnel connection failed: 403 Forbidden')):
            with self.assertRaises(urllib.error.URLError): downloader.check_robots(url)
        with self.assertRaisesRegex(ValueError,'Cached request failure'): downloader.check_robots(url)

    def test_two_command_runs_are_identical_and_unlabeled(self):
        path=self.output/'manifest.json'
        path.write_text(json.dumps(self.manifest))
        with patch('orbit_data.collect.Downloader',side_effect=lambda *a,**kw:SyntheticDownloader(self.output)), redirect_stdout(io.StringIO()):
            self.assertEqual(collect(path,self.output),0)
            before=(self.output/'records.json').read_bytes()
            self.assertEqual(collect(path,self.output),0)
            self.assertEqual(before,(self.output/'records.json').read_bytes())
        records=json.loads(before)
        self.assertFalse(any(r['record_type'] in ('annotation','prediction') for r in records))


if __name__ == '__main__':
    unittest.main()
