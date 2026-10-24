"""Explicit targeted official DIRCO acquisition, separate from positional sampling."""
import json,re,shutil
from datetime import datetime
from orbit_data.validation import ROOT
PRIOR=ROOT.parent/'.local/expansion-v2'
from orbit_data.validation import ROOT,digest
from orbit_data.collect import Downloader
from orbit_data.reviewed import write_immutable
from orbit_data.text import PageText,normalize
out=ROOT.parent/'.local/expansion-v5';out.mkdir(exist_ok=True)
for name in ('raw','cache','text','items'):
 candidate=(ROOT.parent/'.local/expansion-v4')/name
 shutil.copytree(candidate if candidate.exists() else PRIOR/name,out/name,dirs_exist_ok=True)
base=json.loads((PRIOR/'catalog.json').read_text())
entries=[dict(post_id=61309,event_date='2026-02-24',title='Explanation of vote: Support for lasting peace in Ukraine',role='evaluation_reserved'),dict(post_id=51631,event_date='2025-04-24',title='Ramaphosa media briefing on official Ukraine presidential visit',role='development_only'),dict(post_id=39565,event_date='2024-06-16',title='Mufamadi statement, Summit on Peace for Ukraine, 15-16 June 2024',role='development_only')]
entries += [dict(post_id=9188,event_date='2022-04-08',title='Minister Pandor media briefing on Russia-Ukraine conflict',role='development_only'),dict(post_id=53717,event_date='2025-06-19',title='Deputy President Mashatile public lecture in Saint Petersburg',role='development_only')]
for e in entries:e.update(actor_id='ZAF',event_id='event-exp-zaf-dirco-'+str(e['post_id']),url='https://dirco.gov.za/wp-json/wp/v2/posts/'+str(e['post_id']))
write_immutable(ROOT/'source_manifest/targeted-v2/dirco.json',dict(version='1.0.0',selection_method='targeted_training_acquisition',entries=entries,policy='Purposive undercovered ZAF policy statements. Never use this search-selected corpus as a representative country-period sample. Evaluation role fixed before source content or suggestions.'))
write_immutable(ROOT/'workflow/expansion-v1/targeted_split-v2.json',dict(event_roles={e['event_id']:e['role'] for e in entries},reserved_before_suggestions=True,translation_mirror_policy='Group all copies and excerpts with actual communication, including joint events.'))
downloader=Downloader(out,{'dirco.gov.za','www.dirco.gov.za'});outcomes=[]
for e in entries:
 try:
  raw,meta=downloader.download(e['url']);post=json.loads(raw);html=post['content']['rendered']
  if post['status']!='publish' or not post['link'].startswith('https://dirco.gov.za/'):raise ValueError('Post is not a published official source')
  parser=PageText();parser.feed(html);text=normalize(''.join(parser.parts))
  title=PageText();title.feed(post['title']['rendered']);title=normalize(''.join(title.parts))
  if not any(w in (title+' '+text[:1800]).casefold() for w in ('ukraine','ukrainian')):raise ValueError('Source is not about Ukraine')
  if e['event_date'][:4] not in title+' '+text[:1800]:raise ValueError('Event year not corroborated in title/body')
  sha=digest(text.encode());path='text/'+sha+'.txt';(out/path).write_text(text)
  source_date=post['date_gmt']+'Z';issues=[]
  if e['post_id']==39565:issues.append('event_date_range_15_16_June_exact_day_unresolved')
  doc=dict(document_id='doc-exp-zaf-dirco-'+str(e['post_id']),event_id=e['event_id'],actor_id='ZAF',actor_role='focal',year=int(e['event_date'][:4]),session=None,url=e['url'],source_type='official_DIRCO_statement_content_API',fallback=False,record_type='expansion_document',schema_version='1.0.0',delegation='South Africa',speaker='President Cyril Ramaphosa' if e['post_id']==51631 else 'Professor Sydney Mufamadi, National Security Advisor' if e['post_id']==39565 else 'Minister Naledi Pandor' if e['post_id']==9188 else 'Deputy President Shipokosa Paulus Mashatile' if e['post_id']==53717 else 'South African delegation to the UN',speaker_role='Official Republic of South Africa communication',event_date=e['event_date'],metadata_heading=title,language='en',pdf_url=None,event_role=e['role'],canonical_url=post['link'],resolved_url=meta['resolved_url'],issuer='Department of International Relations and Cooperation, Republic of South Africa',publisher='DIRCO',publication_date=source_date[:10],date_basis='Event date in official title; API publication timestamp recorded separately. Summit statement supplies 15-16 June only, exact day held.',retrieved_at=meta['retrieved_at'],landing_retrieved_at=meta['retrieved_at'],raw_path=meta['raw_path'],raw_sha256=meta['raw_sha256'],landing_raw_path=meta['raw_path'],landing_raw_sha256=meta['raw_sha256'],text_path=path,text_sha256=sha,normalization_version='orbit-text-v1',extraction_history=[dict(extractor='DIRCO WordPress published post content.rendered + PageText + orbit-text-v1',status='official_content_without_site_navigation')],pages=None,translation_provenance=None,institutional_scope_status='official_government_issuer_and_named_official_statement_verified',quality_issues=issues,rights_status='private_research_cache_not_cleared_for_public_redistribution',duplicate_of=None,translation_of=None,selection_method='targeted_training_acquisition',source_title=title)
  write_immutable(out/'items'/(doc['document_id']+'.json'),doc);base.append(doc);outcomes.append(dict(event_id=e['event_id'],status='collected',title=title));print(title,len(text),flush=True)
 except Exception as ex:outcomes.append(dict(event_id=e['event_id'],status='blocked',reason=str(ex)));print('BLOCKED',str(ex),flush=True)
write_immutable(out/'catalog.json',base)
old=json.loads((PRIOR/'outcomes.json').read_text());write_immutable(out/'outcomes.json',old+outcomes)
write_immutable(out/'targeted_collection_outcomes.json',outcomes)
