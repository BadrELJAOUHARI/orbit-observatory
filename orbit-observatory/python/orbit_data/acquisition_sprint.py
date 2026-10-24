"""Resumable targeted official acquisition. No new human labels or model fitting."""
import argparse,json,re,io,html,threading,subprocess,tempfile,shutil
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import urlsplit,urljoin,urlencode
from datetime import datetime
from .collect import Downloader,write_json
from .validation import ROOT,digest,load_config
from .text import PageText,normalize

OUT=ROOT.parent/'.local/acquisition-sprint-v1'
ANCHOR=re.compile(r'ukrain|crimea|sevastopol|donbas|donetsk|luhansk|kherson|zaporiz',re.I)
RUSSIA=re.compile(r'russia|kremlin|putin',re.I)
MONTHS='January February March April May June July August September October November December'
LENSES=load_config()[1]
PATTERNS={
 'territorial_recognition':r'territorial integrity|sovereignty|recognised borders|recognized borders|annexation|recogni[sz](?:e|es|ing|ed|tion).{0,60}(?:Crimea|Sevastopol|Donetsk|Luhansk|Kherson|Zaporiz|independence)',
 'troop_withdrawal':r'withdraw|withdrawal|pull.{0,15}troops|leave.{0,25}territor',
 'military_assistance':r'security assistance|military (?:aid|assistance|support|equipment)|armed forces|weapons|arms supplies|defence equipment',
 'sanctions':r'sanctions|restrictive measures|export controls|sanctioned|designat(?:ed|ing)',
 'invasion_responsibility':r'unprovoked|unjustified|aggression|invasion|invaded|launched.{0,40}war|responsib.{0,50}(?:war|invas)|provoked.{0,30}(?:war|invas)'}
LOCKS=defaultdict(threading.Lock)

def military_recipient_is_ukraine(passage):
 """Recipient relation, not co-occurrence of Ukraine and somebody's weapons."""
 p=re.sub(r'\s+',' ',passage)
 return bool(re.search(r'(?:security|military|defen[cs]e)\s+(?:aid|assistance|support|equipment)\s+(?:to|for|in support of)\s+(?:the\s+)?Ukrain|(?:weapons|arms|military equipment).{0,50}\b(?:to|for) (?:the )?Ukrain|(?:provid|suppl|send|deliver|financ|equip|arm).{0,45}Ukrain.{0,80}(?:weapons|military|security assistance)|train.{0,40}Ukrainian (?:armed forces|military)',p,re.I))

def parse_html(body,root=None):
 p=PageText(root);p.feed(body);return normalize(''.join(p.parts))

def date_title(title,fallback):
 m=re.search(r'\b(\d{1,2})\s+('+MONTHS.replace(' ','|')+r')\s+(20\d\d)\b',title,re.I)
 if m:
  try:return datetime.strptime(m.group(),'%d %B %Y').date().isoformat()
  except ValueError:pass
 return fallback[:10] if fallback else None

class Sprint:
 def __init__(self):
  OUT.mkdir(exist_ok=True,parents=True);self.state=json.loads((OUT/'state.json').read_text()) if (OUT/'state.json').exists() else dict(version='1.0.0',queries={},pending=[],done={},batches=0)
  for t in self.state.pop('inflight',[]):
   if t['url'] not in self.state['done'] and t['url'] not in {x['url'] for x in self.state['pending']}:self.state['pending'].append(t)
  self.downloaders={};self.existing_urls=set();self.existing_hashes={}
  # Metadata only: reserved source passages are never opened.
  groups=json.loads((ROOT.parent/'.local/experimental-baseline-v2/leakage_groups.json').read_text())
  self.old_groups=groups
  for path in [ROOT.parent/'.local/expansion-v6/cleared_catalog.json',ROOT.parent/'.local/pilot-v1/records.json']:
   for d in json.loads(path.read_text()):
    if d.get('record_type') not in ('document','expansion_document'):continue
    self.existing_urls.update(d.get(k) for k in ('canonical_url','resolved_url','url') if d.get(k))
    self.existing_hashes[d['text_sha256']]=d['event_id']
  for d in self.docs():self.existing_hashes[d['text_sha256']]=d['event_id']
 def docs(self):return [json.loads(p.read_text()) for p in sorted((OUT/'documents').glob('*.json'))]
 def fetch(self,url):
  host=urlsplit(url).hostname
  with LOCKS[host]:
   if host not in self.downloaders:self.downloaders[host]=Downloader(OUT,{host},interval=1.1)
   return self.downloaders[host].download(url)
 def save(self):write_json(OUT/'state.json',self.state)
 def enqueue(self,t):
  if t['url'].rstrip('/') in {u.rstrip('/') for u in self.existing_urls}:return
  if t['url'] not in self.state['done'] and t['url'] not in {x['url'] for x in self.state['pending']}:self.state['pending'].append(t)
 def query(self,url,handler):
  if url in self.state['queries']:return
  try:
   raw,meta=self.fetch(url);n=handler(raw,meta);self.state['queries'][url]=dict(status='ok',yield_count=n,receipt=meta)
  except Exception as e:self.state['queries'][url]=dict(status='blocked',reason=str(e))
  self.save()
 def discover(self,round_number):
  # Treasury's own documented client-side archive shards, discovered from its search script.
  for year in range(2014,2027):
   def treasury(raw,meta,year=year):
    n=0
    for item in json.loads(raw)['items']:
     if re.search(r'russia|ukrain|crimea|sevastopol',item['title']+' '+item.get('searchText',''),re.I):
      self.enqueue(dict(url=urljoin(meta['resolved_url'],item['url']),actor_id='USA',issuer='U.S. Department of the Treasury',kind='treasury',title=item['title'],event_date=item['date'],method='official_archive_keyword_index_by_year'));n+=1
    return n
   self.query(f'https://home.treasury.gov/news-data/press-releases/search/{year}.json',treasury)
  for search in ['Ukraine','Russia','Crimea','sanctions']:
   for page in range(1,5 if round_number>1 else 3):
    def wp(raw,meta):
     posts=json.loads(raw)
     if not isinstance(posts,list):raise ValueError('No published post list')
     for p in posts:
      title=parse_html(p['title']['rendered']);self.enqueue(dict(url=p['link'],actor_id='ZAF',issuer='Department of International Relations and Cooperation, South Africa',kind='wp',title=title,event_date=date_title(title,p['date_gmt']),post=p,bulk_receipt=meta,method='official_DIRCO_search'))
     return len(posts)
    self.query('https://dirco.gov.za/wp-json/wp/v2/posts?'+urlencode(dict(search=search,per_page=50,page=page)),wp)
  # Bounded auxiliary contrast acquisition; not displayed actors, not assumed opposition.
  for start in [0,100] if round_number>1 else [0]:
   def uk(raw,meta):
    count=0
    for item in json.loads(raw).get('results',[]):
     if item.get('format') not in ('speech','news_story','world_news_story','press_release','statement_to_parliament'):continue
     if not ANCHOR.search(item.get('title','')):continue
     self.enqueue(dict(url='https://www.gov.uk'+item['link'],actor_id='GBR',issuer='UK Government (auxiliary)',kind='govuk',title=item['title'],event_date=item.get('public_timestamp','')[:10],method='official_GOVUK_search'));count+=1
    return count
   self.query('https://www.gov.uk/api/search.json?'+urlencode(dict(q='Ukraine',count=100,start=start)),uk)
  # Targeted Council conclusion series. Non-adopted/procedural documents are rejected.
  ns=[1,4,7,15,18,20,21,24,31] if round_number==1 else [2,3,5,6,8,9,10,12,13,14,16,17,19,22,23,25,27,28,29,30,32]
  for year in range(2014,2027):
   for n in ns:
    self.enqueue(dict(url=f'https://data.consilium.europa.eu/doc/document/ST-{n}-{year}-INIT/en/pdf',actor_id='EU',issuer='European Council / Council of the EU',kind='council',title=f'Council registry {n}/{year}',event_date=None,method='targeted_EUCO_conclusion_series'))
  self.save()
 def retrieve(self,t):
  unmeta=None;unflags=[];landing_receipt=None
  if t['kind']=='un':
   from .expansion_collect import landing_metadata
   from pypdf import PdfReader
   raw,landing_receipt=self.fetch(t['url']);unmeta=landing_metadata(raw,t['url'],t['actor_id'])
   if not unmeta['event_date'].startswith(str(t['year'])):raise ValueError('UN landing/date year mismatch; copy held')
   raw,meta=self.fetch(unmeta['pdf_url'])
   if not raw.startswith(b'%PDF'):raise ValueError('UN attachment not PDF')
   text=normalize('\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(raw)).pages))
   title=f"{unmeta['delegation']} — {unmeta['speaker']} — UN General Debate {t['year']}"
   t['event_date']=unmeta['event_date'];published=None
   if len(re.findall(r'/\d+|/i255',text))>100:
    (OUT/'extraction_failures').mkdir(exist_ok=True)
    failure=OUT/'extraction_failures'/(digest(t['url'].encode())+'.txt');failure.write_text(text)
    write_json(failure.with_suffix('.json'),dict(source_url=t['url'],source_receipt=meta,text_sha256=digest(text.encode()),text_path=str(failure),status='held_unusable_font_mapping_not_conflict_rejection'))
    raise ValueError('PDF font mapping extraction failure; cached original and failed extraction retained')
   if unmeta['language']!='en':unflags.append('language_review')
   if re.search(r'UNOFFICIAL|COURTESY TRANSLATION|English Rendition',text[:2500],re.I) or t['actor_id'] in ('TUR','RUS','UKR'):unflags.append('translation_review')
   if t['actor_id']=='EU' and not re.search(r'on behalf of (?:the )?European Union|au nom de l.Union europ',text,re.I):unflags.append('EU_common_position_review')
  elif t['kind']=='wp':
   meta=t['bulk_receipt'];post=t['post'];text=parse_html(post['content']['rendered']);title=t['title'];published=post['date_gmt'][:10]
  elif t['kind']=='mea':
   raw,meta=self.fetch('https://www.mea.gov.in/FrontEnd/FetchPublicationDetailData?'+urlencode(dict(pkid=t['pkid'],languageId=1)));text=parse_html(raw.decode());title=t['title'];published=t['event_date']
  elif t['kind']=='govuk':
   raw,meta=self.fetch('https://www.gov.uk/api/content'+urlsplit(t['url']).path);p=json.loads(raw)
   text=parse_html(p.get('details',{}).get('body',''));title=p['title'];published=(p.get('first_published_at') or p.get('public_updated_at') or '')[:10]
   t['event_date']=date_title(title,published)
  else:
   raw,meta=self.fetch(t['url']);published=t.get('event_date')
   if t['kind']=='council':
    if not raw.startswith(b'%PDF'):raise ValueError('Not PDF')
    with tempfile.TemporaryDirectory() as tmp:
     p=Path(tmp)/'input.pdf';p.write_bytes(raw);s=subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,text=True,check=True).stdout
    text=normalize(s);title=t['title']
    if not re.search(r'conclusions\s+adopted|as\s+approved\s+by\s+the\s+Council',text[:4500],re.I):raise ValueError('Not an adopted Council conclusion/position')
    m=re.search(r'Brussels\s*,?\s*(\d{1,2})\s+('+MONTHS.replace(' ','|')+r')\s+(20\d\d)',text[:1600],re.I)
    if not m:raise ValueError('No documentary adoption date')
    t['event_date']=date_title(m.group(),None);published=None
   else:
    rawtext=raw.decode('utf-8');text=parse_html(rawtext,'main');title=t['title']
  if len(text)<300:raise ValueError('Missing usable official body')
  if not t.get('event_date') or not '2014-01-01'<=t['event_date']<='2026-10-24':raise ValueError('Missing/out-of-period event date')
  if not ANCHOR.search(text):raise ValueError('No Ukraine/territory conflict anchor')
  if re.search(r'joint statement|joint declaration|G7 |G20 ',title,re.I):joint=True
  else:joint=False
  if t['kind']=='mea' and re.search(r'transcript|question|joint|briefing',title,re.I):attribution_hold=True
  elif t['kind']=='wp' and not re.search(r'statement|remarks|address|speech|briefing|explanation|minister|president',title,re.I):attribution_hold=True
  else:attribution_hold=False
  sha=digest(text.encode());event='event-sprint-'+digest((t['actor_id']+':'+t['event_date']+':'+re.sub(r'\W','',title.casefold())).encode())[:24]
  # Freeze label-independent partition before extracting/suggesting anything.
  role='evaluation_reserved' if int(digest(('sprint-split-2026:'+event).encode())[:8],16)%10==0 else 'development_only'
  duplicate=self.existing_hashes.get(sha)
  if duplicate:
   event=duplicate
   if event in self.old_groups['event_groups'] and self.old_groups['event_groups'][event] in self.old_groups['reserved_leakage_group_ids']:role='evaluation_reserved'
  doc=dict(id='doc-sprint-'+digest(t['url'].encode())[:24],actor_id=t['actor_id'],actor_role='auxiliary_training_only' if t['actor_id'] in ('GBR','RUS','UKR') else 'focal',issuer=t['issuer'],
   speaker=t['issuer'] if t['kind'] in ('treasury','council') else title,speaker_basis='Official issuing institution' if t['kind'] in ('treasury','council') else 'Named office/statement title; quoted third-party passages held separately',
   canonical_url=t['url'],source_type=t['kind'],title=title,event_date=t['event_date'],publication_date=published,retrieved_at=meta['retrieved_at'],language='en',
   translation_provenance='Original English institutional version' if t['kind'] in ('treasury','council','govuk') else 'English official publication; original-language equivalence not asserted',
   text_sha256=sha,text_path='text/'+sha+'.txt',source_receipt=meta,acquisition_method=t['method'],acquisition_stream='targeted_training_acquisition_not_position_estimation',
   event_id=event,event_role=role,duplicate_of=duplicate,translation_of=None,joint_statement=joint,attribution_hold=attribution_hold,normalization='sprint-text-1: NFC, strip/collapse horizontal whitespace on physical lines; paragraph/sentence windows map to unchanged stored text')
  if unmeta:
   doc.update(speaker=unmeta['speaker'],speaker_basis='Official UN delegation landing heading: '+unmeta['speaker_role'],language=unmeta['language'],translation_provenance='Delegation-submitted official UN archive attachment; '+('; '.join(unflags) or 'English original publication; no translation inferred'),source_quality_flags=unflags,landing_receipt=landing_receipt,attachment_url=unmeta['pdf_url'])
  (OUT/'text').mkdir(exist_ok=True);(OUT/doc['text_path']).write_text(text)
  (OUT/'documents').mkdir(exist_ok=True);write_json(OUT/'documents'/(doc['id']+'.json'),doc)
  return doc
 def discover_gaps(self):
  """Bounded focal gap search; resume once per exact query, including failures."""
  for term in ('sanctions','Ukraine','Crimea','Russian Federation'):
   for page in (1,2,3):
    def wp(raw,meta):
     posts=json.loads(raw)
     if not isinstance(posts,list):raise ValueError('No official post list')
     for p in posts:
      title=parse_html(p['title']['rendered'])
      self.enqueue(dict(url=p['link'],actor_id='ZAF',issuer='Department of International Relations and Cooperation, South Africa',kind='wp',title=title,event_date=date_title(title,p['date_gmt']),post=p,bulk_receipt=meta,method='focal_gap_DIRCO_small_page_search_v1'))
     return len(posts)
    self.query('https://dirco.gov.za/wp-json/wp/v2/posts?'+urlencode(dict(search=term,per_page=10,page=page,_fields='id,date_gmt,link,title,content')),wp)
  self.save()
 def discover_earlier_council(self):
  # Bounded EUCO-number/year series, never an indiscriminate registry crawl.
  # Expands the undercovered 2014-2021 period, with adopted-position/date gates.
  for year in range(2014,2022):
   for n in [2,3,5,6,8,9,10,12,13,14,16,17,19,22,23,25,27,28,29,30,32]:
    self.enqueue(dict(url=f'https://data.consilium.europa.eu/doc/document/ST-{n}-{year}-INIT/en/pdf',actor_id='EU',issuer='European Council / Council of the EU',kind='council',title=f'Council registry {n}/{year}',event_date=None,method='bounded_adopted_EUCO_earlier_period_gap_v1'))
  self.save()
 def discover_un_gaps(self):
  from .expansion_collect import ACTORS
  # Supplementary only: direct actor-domain routes were tried first.
  years={'USA':[2019,2020,2021,2025,2026],'EU':[2019,2020,2026],'TUR':[2014,2018,2019,2020,2021,2025,2026],'IND':[2015,2019,2020,2021,2026],'ZAF':[2019,2020,2026],'RUS':[2023,2024,2025,2026],'UKR':[2023,2025,2026]}
  for actor,ys in years.items():
   name,slug=ACTORS[actor]
   for year in ys:self.enqueue(dict(url=f'https://gadebate.un.org/en/{year-1945}/{slug}',actor_id=actor,issuer=name+' official delegation to the UN',kind='un',title=f'{name} UN General Debate {year}',year=year,event_date=None,method='supplementary_official_UN_missing_event_gap_v1'))
  self.save()
 def process(self,batch_size):
  batch=self.state['pending'][:batch_size];self.state['inflight']=batch;self.state['pending']=self.state['pending'][batch_size:];self.save()
  with ThreadPoolExecutor(max_workers=5) as pool:
   futures={pool.submit(self.retrieve,t):t for t in batch}
   for f in as_completed(futures):
    t=futures[f]
    try:
     doc=f.result();self.existing_hashes.setdefault(doc['text_sha256'],doc['event_id']);self.state['done'][t['url']]=dict(status='downloaded',document_id=doc['id'])
    except Exception as e:self.state['done'][t['url']]=dict(status='rejected_or_inaccessible',reason=str(e))
    self.save()
  self.state['inflight']=[];self.state['batches']+=1;self.save();self.export()
 def export(self):
  docs=self.docs();accepted=[];held=[];rejected=[];duplicates=[];seen={};reserved=[]
  for doc in docs:
   if doc['duplicate_of']:duplicates.append(dict(document_id=doc['id'],duplicate_of=doc['duplicate_of']));continue
   text=(OUT/doc['text_path']).read_text();windows=[]
   # Paragraph windows in HTML; full sentences rejoined across PDF lines with source envelopes.
   if doc['source_type']=='un':
    from .resegment import source_lines,units
    raw=(OUT/doc['source_receipt']['raw_path']).read_bytes()
    try:windows=[(u['start'],u['end']) for u in units(text,source_lines(text,raw))[0]]
    except Exception:
     windows=[(m.start(),m.end()) for m in re.finditer(r'[^\n]+',text)];doc.setdefault('source_quality_flags',[]).append('PDF_layout_alignment_review')
   elif doc['source_type']=='council':
    for m in re.finditer(r'(?:^|\n)(?:\d{1,2}\.\s+)?[^\n]+(?:\n(?!\d{1,2}\.\s|EUCO |EN$|\d+$)[^\n]+)*',text):windows.append((m.start(),m.end()))
   else:windows=[(m.start(),m.end()) for m in re.finditer(r'[^\n]+',text) if len(m.group())>=65]
   for a,b in windows:
    passage=text[a:b];before=text[max(0,a-500):a];after=text[b:b+350];local=before+' '+passage+' '+after
    if not ANCHOR.search(passage) and not (ANCHOR.search(before[-400:]) and re.search(r'\b(?:these|this|such|Russia|Russian|sanctions|weapons)\b',passage,re.I)):continue
    if len(passage)>2800 or len(passage)<65:continue
    for lens,pattern in PATTERNS.items():
     if not re.search(pattern,passage,re.I):continue
     if doc['event_date']<LENSES[lens]['applicable_from']:continue
     reasons=list(doc.get('source_quality_flags',[]))
     if lens=='invasion_responsibility' and not re.search(r'(?:russia|russian|kremlin|putin).{0,100}(?:aggress|inva|unprovoked|launched)|(?:aggress|inva).{0,100}(?:russia|russian|kremlin|putin)',passage,re.I|re.S):continue
     if lens=='military_assistance' and not military_recipient_is_ukraine(passage):continue
     if lens=='troop_withdrawal' and re.search(r'pre[ -]?(?:24|February)|except.{0,20}Crimea|excluding.{0,20}Crimea',passage,re.I):reasons.append('W1_territorial_exception_or_preinvasion_line')
     if lens=='troop_withdrawal' and not re.search(r'(?:Russian|Russia.s).{0,45}(?:forces|troops|military|soldiers).{0,100}withdraw|withdraw.{0,100}(?:Russian|Russia.s).{0,35}(?:forces|troops|military|soldiers)|Russia.{0,100}withdraw.{0,100}(?:territor|Ukraine)',passage,re.I|re.S):continue
     if lens=='sanctions' and not (RUSSIA.search(local) and ANCHOR.search(local)):continue
     if re.search(r'Zimbabwe|North Korea|Iran|Gaza|Palestin|Sudan',passage,re.I) and not (ANCHOR.search(passage) and RUSSIA.search(passage)):
      rejected.append(dict(document_id=doc['id'],start=a,end=b,lens_id=lens,reason='Other conflict/policy subject'));continue
     if re.search(r'SANCTIONS IMPLICATIONS|50 percent|all property and interests|blocked persons|OFAC regulations',passage,re.I):
      rejected.append(dict(document_id=doc['id'],start=a,end=b,lens_id=lens,reason='Regulatory boilerplate, not policy position'));continue
     if doc['joint_statement']:reasons.append('joint_signatory_attribution_review')
     if doc['attribution_hold'] and not (doc['source_type']=='wp' and re.search(r'South Africa (?:calls|supports|condemns|opposes|rejects|reiterates|believes)',passage,re.I)):reasons.append('speaker_role_review')
     if doc['actor_id']!='RUS' and re.search(r'(?:Russia|Putin|Kremlin) (?:says|claims|argues|insists|demands|refuses|announced|believes|has said)',passage,re.I):reasons.append('reported_foreign_position_attribution_review')
     own_quote=doc['source_type']=='treasury' and len(re.findall(r'\bsaid\b',passage,re.I))==1 and re.search(r'said (?:Under Secretary|Deputy Secretary|Assistant Secretary|Secretary of the Treasury|Treasury Secretary)',passage,re.I)
     if re.search(r'[“”"]|\b(?:said|according to)\b',passage,re.I) and not own_quote:reasons.append('quoted_speaker_review')
     if lens=='territorial_recognition' and not (re.search(r'internationally (?:recogni[sz]ed)|1991',passage,re.I) and re.search(r'(?:never|not|non)[ -]?(?:recogn|accept)|illegal annex',passage,re.I)):reasons.append('partial_territorial_scope')
     if lens=='troop_withdrawal' and not re.search(r'(?:all|entire|complete|fully).{0,120}(?:territor|withdraw)|withdraw.{0,120}(?:all|entire|internationally)',passage,re.I|re.S):reasons.append('W1_scope_not_established')
     if re.search(r'\b(?:co nt|exam ple|terr it|sanc tions|contin ue)\b|[\uf000-\uf8ff]',passage):reasons.append('extraction_review')
     if doc['source_type']=='treasury' and re.search(r' designated |is designated|being designated',passage,re.I) and not re.search(r'war|invas|aggress|Ukraine|undermin|occupation',passage,re.I):reasons.append('legal_implementation_only')
     key=digest((lens+':'+re.sub(r'\s+',' ',passage.casefold()).strip()).encode())
     if key in seen:duplicates.append(dict(document_id=doc['id'],start=a,end=b,lens_id=lens,duplicate_of=seen[key]));continue
     cid='claim-sprint-'+digest(f"{doc['id']}:{a}:{b}:{lens}".encode());seen[key]=cid
     record=dict(candidate_id=cid,document_id=doc['id'],event_id=doc['event_id'],event_role=doc['event_role'],actor_id=doc['actor_id'],actor_role=doc['actor_role'],event_date=doc['event_date'],lens_id=lens,proposition=LENSES[lens]['definition'],
      issuer=doc['issuer'],speaker=doc['speaker'],source_url=doc['canonical_url'],language=doc['language'],translation_provenance=doc['translation_provenance'],text_sha256=doc['text_sha256'],start=a,end=b,exact_passage=passage,
      context_before=before,context_after=after,quality_flags=reasons,human_label='',annotator_id=None,training_approved=False,acquisition_method=doc['acquisition_method'])
     if doc['event_role']=='evaluation_reserved':reserved.append(record)
     elif reasons:held.append(record)
     else:accepted.append(record)
  for name,value in [('clean.json',accepted),('held.json',held),('rejected.json',rejected),('duplicates.json',duplicates),('evaluation.json',reserved)]:write_json(OUT/name,value)
  report=dict(documents=len(docs),attempted=len(self.state['done']),pending=len(self.state['pending']),clean_pairs=len(accepted),clean_events=len({r['event_id'] for r in accepted}),clean_passages=len({(r['document_id'],r['start'],r['end']) for r in accepted}),held_pairs=len(held),evaluation_pairs=len(reserved),rejected_pairs=len(rejected),duplicates=len(duplicates),
   by_actor={actor:dict(pairs=sum(r['actor_id']==actor for r in accepted),events=len({r['event_id'] for r in accepted if r['actor_id']==actor}),lenses=dict(Counter(r['lens_id'] for r in accepted if r['actor_id']==actor))) for actor in ['USA','EU','TUR','IND','ZAF','GBR']},
   years=dict(Counter(r['event_date'][:4] for r in accepted)),approved_new_labels=0,suggestion_generation='pending contextual-rule pass; no human review/training approval',batches=self.state['batches'])
  report.update(provisional=True,caveat='Before final boundary, previous-source, copied-passage and connected-split audit; not the final clean count')
  write_json(OUT/'yield.json',report);write_json(OUT/'source_event_manifest.json',docs)
  write_json(OUT/'last_batch_checkpoint.json',dict(batches=self.state['batches'],pending_urls=[t['url'] for t in self.state['pending']],queries=len(self.state['queries']),yield_counters=report))
  print(json.dumps(report),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--round',type=int,default=1);p.add_argument('--batches',type=int,default=20);p.add_argument('--batch-size',type=int,default=30);p.add_argument('--resume',action='store_true');p.add_argument('--discover-gaps',action='store_true');p.add_argument('--discover-earlier-council',action='store_true');p.add_argument('--discover-un-gaps',action='store_true');p.add_argument('--finalize',action='store_true');args=p.parse_args()
 s=Sprint()
 if not args.resume:s.discover(args.round)
 if args.discover_gaps:s.discover_gaps()
 if args.discover_earlier_council:s.discover_earlier_council()
 if args.discover_un_gaps:s.discover_un_gaps()
 for _ in range(args.batches):
  if not s.state['pending']:break
  s.process(args.batch_size)
 if args.finalize:
  from .sprint_review import build
  build()
if __name__=='__main__':main()
