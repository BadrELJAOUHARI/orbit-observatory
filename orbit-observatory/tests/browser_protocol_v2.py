import sys,json,csv,io,tempfile,threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from orbit_data.protocol_v2 import OUT,validate,eligible
class H(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
s=ThreadingHTTPServer(('127.0.0.1',0),partial(H,directory=str(OUT)));threading.Thread(target=s.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{s.server_port}/review.html');assert not errors,errors
 assert page.locator('fieldset').count()==780
 row=page.locator('fieldset').filter(has=page.locator('[data-field=integrity_direction]')).first
 row.locator('[data-field=integrity_direction]').select_option('support');row.locator('[data-field=annotator_id]').fill('SYNTHETIC');row.locator('[data-field=review_notes]').fill('Synthetic UI check, never imported');cid=row.get_attribute('data-id');page.reload();assert page.locator('fieldset[data-id="'+cid+'"] [data-field=integrity_direction]').input_value()=='support'
 page.evaluate("""()=>{URL.createObjectURL=b=>{window.testBlob=b;return 'blob:test'};HTMLAnchorElement.prototype.click=function(){}}""");page.locator('#csv').click();text=page.evaluate('async()=>await window.testBlob.text()');rows=list(csv.DictReader(io.StringIO(text.lstrip('\ufeff'))));assert len(validate(rows))==1
 page.locator('#json').click();backup=page.evaluate('async()=>await window.testBlob.text()')
 with tempfile.TemporaryDirectory(prefix='orbit-v2-synthetic-',dir='/tmp') as directory:
  from pathlib import Path
  path=Path(directory)/'progress.json';path.write_text(backup)
  fresh=b.new_context();other=fresh.new_page();other.goto(f'http://127.0.0.1:{s.server_port}/review.html');other.locator('#import').set_input_files(str(path));other.wait_for_function("document.querySelector('#saved').textContent.includes('Imported successfully')")
  assert other.locator('fieldset[data-id="'+cid+'"] [data-field=integrity_direction]').input_value()=='support'
  csvpath=Path(directory)/'returned.csv';csvpath.write_text(text)
  other.locator('#import').set_input_files(str(csvpath));other.wait_for_function("document.querySelector('#saved').textContent.includes('Imported successfully')")
  old=Path('/workspace/orbit-observatory/.local/development-review-sprint-v1/orbit-development-review.csv')
  with old.open(encoding='utf-8-sig',newline='') as f:legacy=list(csv.DictReader(f))
  legacy[0].update(human_label='support',human_annotator_id='SYNTHETIC',human_review_notes='Synthetic saved response',human_attribution='wrong_actor')
  path=Path(directory)/'legacy.csv'
  with path.open('w',encoding='utf-8',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=list(legacy[0]));writer.writeheader();writer.writerows(legacy)
  other.locator('#import').set_input_files(str(path));other.wait_for_function("document.querySelector('#saved').textContent.includes('Imported successfully')")
  legacy_id=legacy[0]['candidate_id'];assert other.locator('fieldset[data-id="'+legacy_id+'"] [data-field=strict_label]').input_value()=='support'
  assert other.locator('fieldset[data-id="'+legacy_id+'"] [data-field=attribution_quality]').input_value()=='wrong_actor'
  fresh.close()
 rows[0]['exact_passage']='tampered'
 try:validate(rows);raise AssertionError('tamper accepted')
 except ValueError:pass
 assert not errors,errors;b.close()
s.shutdown();print('PASS 780 tasks; independent component fields; autosave/reload; complete CSV roundtrip; immutable tamper rejection')
