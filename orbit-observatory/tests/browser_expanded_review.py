"""Synthetic UI responses only; never imported as canonical annotations."""
import csv,json,tempfile,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from orbit_data.review_import import select_baseline,validate_return

from orbit_data.validation import ROOT
root=ROOT.parent/'.local/development-review-expanded-v2-20261023'
rows=json.loads((root/'review_queue.json').read_text())
manifest=json.loads((root/'manifest.json').read_text())
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)+'/orbit-development-review.html'
errors=[]
def download(page,button,path):
 with page.expect_download() as d:page.locator(button).click()

 try:d.value.save_as(path)
 except Exception as e:
  print('DOWNLOAD DEBUG',path,'page_closed',page.is_closed(),'url',d.value.url,'error',str(e));raise
def start(p,profile):
 return p.chromium.launch_persistent_context(profile,headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'],accept_downloads=True)
profile=tempfile.mkdtemp(prefix='orbit-dev-synthetic-profile-',dir='/tmp')
with sync_playwright() as p:
 context=start(p,profile);page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
 assert page.locator('article').count()==manifest['records']
 assert page.locator('article:visible').count()==manifest['new_clean_records']
 payload=json.loads(page.locator('#packet-data').text_content())
 assert all(r['event_role']=='development_only' for r in payload['rows'])
 assert len({r['event_id'] for r in payload['rows']})==len(manifest['events'])
 page.locator('#status-filter').select_option('all');page.locator('#quality-filter').select_option('all')
 assert page.locator('article:visible').count()==manifest['records']
 page.locator('#quality-filter').select_option('quarantined');assert page.locator('article:visible').count()==manifest['quarantined']
 page.locator('#quality-filter').select_option('clean');assert page.locator('article:visible').count()==manifest['mechanically_clean']
 page.locator('#status-filter').select_option('unreviewed');assert page.locator('article:visible').count()==manifest['new_clean_records']
 article=page.locator('article:visible').first
 index=int(article.get_attribute('data-index'));cid=rows[index]['candidate_id'];row_id=rows[index]['row_id']
 page.locator('#annotator').fill('SYNTHETIC_UI_TEST_ONLY')
 article.locator('[data-field=human_label]').select_option('no_stance')
 notes='Synthetic UI only: "café", commas\nand a second line. Never import as a research annotation.'
 article.locator('textarea').fill(notes)
 assert article.is_visible(),'Editing should not disappear while typing'
 assert article.locator('[data-field=human_annotator_id]').input_value()=='SYNTHETIC_UI_TEST_ONLY'
 assert 'Saved locally' in page.locator('#save-status').inner_text()
 page.locator('#status-filter').select_option('all')
 download(page,'#export-csv','/tmp/orbit-expanded-synthetic-return.csv')
 download(page,'#export-json','/tmp/orbit-expanded-synthetic-backup.json')
 with open('/tmp/orbit-expanded-synthetic-return.csv',encoding='utf-8-sig',newline='') as f:returned=list(csv.DictReader(f))
 assert len(returned)==manifest['records']
 _,baseline=select_baseline(returned);assert len(validate_return(returned,baseline))==1
 answer=next(r for r in returned if r['candidate_id']==cid)
 assert answer['human_review_notes']==notes and answer['human_independent']=='false'
 for old,new in zip(rows,returned):
  for key in ['existing_annotation_id','existing_label','existing_provenance','existing_review_notes','ai_suggested_label','event_id','exact_passage','context_before','context_after']:
   assert str(old[key])==new[key],key
 page.reload();assert 'Restored saved progress' in page.locator('#save-status').inner_text()
 assert page.locator('#'+row_id+' textarea').input_value()==notes
 context.close()
 context=start(p,profile);page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
 assert page.locator('#'+row_id+' textarea').input_value()==notes,'Browser restart lost progress'
 # The managed Chromium build crashes in its persistent-profile download handler
 # (NSS database initialization). Capture the actual exported Blob after restart;
 # real download handling is checked independently in fresh contexts below.
 page.evaluate("""() => {const create=URL.createObjectURL;URL.createObjectURL=(blob)=>{window.__exportedBlob=blob;return create(blob)};HTMLAnchorElement.prototype.click=function(){};}""")
 page.locator('#export-csv').click()
 exported=page.evaluate('async () => await window.__exportedBlob.text()')
 Path('/tmp/orbit-expanded-synthetic-reopened.csv').write_text(exported,encoding='utf-8')
 with open('/tmp/orbit-expanded-synthetic-reopened.csv',encoding='utf-8-sig',newline='') as f:reopened=list(csv.DictReader(f))
 assert reopened==returned
 context.close()
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 # Separate contexts represent another browser/profile with no local progress.
 for extension,path in [('json','/tmp/orbit-expanded-synthetic-backup.json'),('csv','/tmp/orbit-expanded-synthetic-return.csv')]:
  fresh=browser.new_context(accept_downloads=True);page=fresh.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
  page.locator('#import-file').set_input_files(path)
  page.wait_for_function("document.getElementById('import-status').textContent.startsWith('Imported')")
  assert page.locator('#'+row_id+' textarea').input_value()==notes
  assert page.locator('#'+row_id+' [data-field=human_label]').input_value()=='no_stance'
  download(page,'#export-csv',f'/tmp/orbit-expanded-{extension}-roundtrip.csv')
  with open(f'/tmp/orbit-expanded-{extension}-roundtrip.csv',encoding='utf-8-sig',newline='') as f:assert list(csv.DictReader(f))==returned
  if extension=='csv':
   tampered=[dict(r) for r in returned];tampered[0]['exact_passage']='SYNTHETIC TAMPERING TEST'
   with open('/tmp/orbit-expanded-invalid.csv','w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(tampered[0]));writer.writeheader();writer.writerows(tampered)
   page.locator('#import-file').set_input_files('/tmp/orbit-expanded-invalid.csv')
   page.wait_for_function("document.getElementById('import-status').textContent.startsWith('Import failed')")
   assert page.locator('#'+row_id+' textarea').input_value()==notes
   modified=json.loads(Path('/tmp/orbit-expanded-synthetic-backup.json').read_text())
   modified['responses'][cid]['human_review_notes']='SYNTHETIC EXPLICIT REPLACEMENT TEST'
   Path('/tmp/orbit-expanded-conflict.json').write_text(json.dumps(modified))
   page.locator('#import-file').set_input_files('/tmp/orbit-expanded-conflict.json')
   page.wait_for_function("document.getElementById('import-status').textContent.includes('Different local responses')")
   assert page.locator('#'+row_id+' textarea').input_value()==notes
   page.locator('#allow-replace').check();page.locator('#import-file').set_input_files('/tmp/orbit-expanded-conflict.json')
   page.wait_for_function("document.getElementById('import-status').textContent.startsWith('Imported')")
   page.reload();assert page.locator('#'+row_id+' textarea').input_value()=='SYNTHETIC EXPLICIT REPLACEMENT TEST'
  fresh.close()
 # Browser storage denial must show an honest failure and retain manual export.
 denied=browser.new_context(accept_downloads=True)
 denied.add_init_script("Storage.prototype.setItem=function(){throw new DOMException('Synthetic denied storage','SecurityError')};")
 page=denied.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
 assert 'Could not restore/save' in page.locator('#save-status').inner_text()
 download(page,'#export-json','/tmp/orbit-expanded-storage-denied-backup.json')
 assert 'Local saving unavailable' in page.locator('#save-status').inner_text()
 denied.close();browser.close()
assert errors==[],errors
server.shutdown();server.server_close()
print('PASS: Expanded development-only rows; clean/quarantine/unreviewed filters; autosave across reload and full browser restart; CSV/JSON round-trips preserve decisions and provenance; tampering/conflict guards; explicit replacement; storage-denial fallback; zero page errors. All responses synthetic and confined to /tmp.')
