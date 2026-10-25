"""Resumable focal acquisition. Leaves sprint-v1 records and packet immutable."""
import argparse,html,json,re,subprocess,tempfile
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit,urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
from .focal_retrieval import OUT,OLD,Store,page,historical_metadata
from .collect import write_json
from .validation import ROOT,digest
from .text import normalize
from .acquisition_sprint import ANCHOR,MONTHS,date_title

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.current=None
    def handle_starttag(self,t,a):
        if t=='a':self.current=[dict(a).get('href',''),'']
    def handle_data(self,d):
        if self.current:self.current[1]+=d
    def handle_endtag(self,t):
        if t=='a' and self.current:self.links.append(tuple(self.current));self.current=None

def links(raw):
    p=Links();p.feed(raw.decode());return p.links

def date_value(text):
    m=re.search(r'\b(\d{1,2})\s+('+MONTHS.replace(' ','|')+r'),?\s+(20\d\d)\b',text,re.I)
    if m:return date_title(m.group().replace(',',''),None)
    m=re.search(r'\b('+MONTHS.replace(' ','|')+r')\s+(\d{1,2}),?\s+(20\d\d)\b',text,re.I)
    if m:return date_title(m[2]+' '+m[1]+' '+m[3],None)

def canonical_key(url):
    from urllib.parse import unquote
    m=re.search(r'dtl/(\d+)',url)
    return 'mea:'+m[1] if m else unquote(url).rstrip('/').casefold()

class Acquisition:
    def __init__(self):
        self.store=Store();self.path=OUT/'state.json'
        self.state=json.loads(self.path.read_text()) if self.path.exists() else dict(version='focal-acquisition-2.0.0',queries={},pending_queries=[],pending_urls=[],done={},batches=0)
        for t in self.state.pop('inflight',[]):
            if t['url'] not in self.state['done'] and t['url'] not in {p['url'] for p in self.state['pending_urls']}:self.state['pending_urls'].append(t)
        self.old_docs=historical_metadata()
        self.existing={canonical_key(d[k]) for d in self.old_docs for k in ['canonical_url','resolved_url','url','pdf_url'] if d.get(k)}
        self.protected={(d['actor_id'],d['event_date']) for d in self.old_docs if d['event_role']=='evaluation_reserved'}
        self.old_by_hash={d['text_sha256']:d for d in self.old_docs}
    def save(self):write_json(self.path,self.state)
    def query(self,actor,url,kind,**kw):
        self.state.setdefault('query_definitions',{})[url]=dict(actor_id=actor,url=url,kind=kind,**kw)
        if url not in self.state['queries'] and url not in {t['url'] for t in self.state['pending_queries']}:self.state['pending_queries'].append(dict(actor_id=actor,url=url,kind=kind,**kw))
    def enqueue(self,t):
        self.state.setdefault('source_definitions',{})[t['url']]={k:v for k,v in t.items() if k not in ('post','index')}
        key=canonical_key(t['url'])
        if key in self.existing:return
        if t['url'] not in self.state['done'] and key not in {canonical_key(p['url']) for p in self.state['pending_urls']}:self.state['pending_urls'].append(t)
    def plan(self):
        # Public forms/endpoints discovered from the institutions' own HTML.
        self.query('TUR','https://www.mfa.gov.tr/press-information.en.mfa','mfa_categories')
        for term in ['Ukraine','Crimea','sanctions','military assistance']:
            for p in range(1,4 if term=='Ukraine' else 2):
                u='https://www.mea.gov.in/FrontEnd/FetchPublicationListingData?'+urlencode(dict(publicationId=0,KeywordName=term,SortBy='desc',page=p,PageSize=100,DateRange='',IsInternalMEA='false',PLngId=1))
                self.query('IND',u,'mea_listing',term=term)
        # Reuse the saved successful initial listing, including its exact URL case.
        m=json.loads((OLD/'mea_discovery.json').read_text());self.query('IND',m['url'],'mea_listing',term='Ukraine')
        for term in ['Ukraine','Crimea','Ukraine sanctions','Ukraine weapons','Ukraine withdrawal']:
            pages=range(1,10) if term=='Ukraine' else range(1,3)
            for p in pages:
                model=dict(searchType=1,searchText=term,sections=[],tags=[],fromDate='2014-01-01',toDate='2026-10-24',isExactSearch=False,isPdfSearch=False,page=p,pageSize=100,sortBy='Relevance',searchBy='title+content',resultFields=[])
                self.query('IND','https://www.mea.gov.in/FrontEnd/AdvanceSearchDetails#'+digest(json.dumps(model,sort_keys=True).encode()),'mea_fulltext',model=model)
        for term in ['Ukraine','Crimea','Russia sanctions']:
            for p in range(3):self.query('ZAF','https://www.gov.za/search?'+urlencode(dict(search_query=term,page=p)),'govza_search')
        for term in ['Russia','Ukraine','sanctions']:
            for p in range(1,4):self.query('ZAF','https://dirco.gov.za/wp-json/wp/v2/posts?'+urlencode(dict(search=term,per_page=10,page=p,_fields='id,date_gmt,link,title,content')),'wp')
        for y in range(2014,2027):
            for n in [11,26]:self.enqueue(dict(actor_id='EU',url=f'https://data.consilium.europa.eu/doc/document/ST-{n}-{y}-INIT/en/pdf',kind='council',title=f'Council adopted-position gap {n}/{y}',method='bounded_missing_EUCO_number_gap'))
        self.save()
    def discover_one(self,t):
        if t['kind']=='mea_fulltext':
            raw,m=self.store.public_json(t['url'].split('#')[0],t['model'])
        elif t['kind']=='mfa_postback':
            if t.get('form_parent_receipt'):original=(OUT/t['form_parent_receipt']['raw_path']).read_bytes()
            else:original,_=self.store.get(t['base_url'])
            if not re.search(r'Page\$'+str(t['page_number'])+r'(?!\d)',html.unescape(original.decode())):
                raise ValueError('Discovery failure: requested page not advertised in the supplied public form')
            class Form(HTMLParser):
                def __init__(self):super().__init__();self.fields={}
                def handle_starttag(self,tag,attrs):
                    a=dict(attrs)
                    if tag=='input' and a.get('type')=='hidden' and a.get('name'):self.fields[a['name']]=a.get('value','')
            form=Form();form.feed(original.decode());form.fields.update(__EVENTTARGET='sb$grd',__EVENTARGUMENT='Page$'+str(t['page_number']))
            raw,m=self.store.public_form(t['base_url'],form.fields)
        else:raw,m=self.store.get(t['url'])
        ls=links(raw) if not raw.lstrip().startswith((b'[',b'{')) else []
        before=len(self.state['pending_urls'])
        if t['kind']=='mfa_categories':
            for h,title in ls:
                if title.strip() in ['Press Releases & Statements','Question & Answer','Joint Declarations','Press Conferences']:
                    self.query('TUR',urljoin(t['url'],h),'mfa_years',category=title.strip())
        elif t['kind']=='mfa_years':
            for h,title in ls:
                if re.fullmatch(r'20(?:1[4-9]|2[0-6])',title.strip()):self.query('TUR',urljoin(t['url'],h),'mfa_year_archive',category=t['category'],year=int(title.strip()),depth=0)
                elif ANCHOR.search(h+' '+title):self.enqueue(dict(actor_id='TUR',url=urljoin(t['url'],h),kind='mfa',title=title.strip(),method='official_MFA_dated_archive'))
        elif t['kind'] in ('mfa_year_archive','mfa_postback'):
            for h,title in ls:
                u=urljoin(t.get('base_url',t['url']),h)
                if ANCHOR.search(h+' '+title) and '.en.mfa' in h and not h.startswith('javascript'):self.enqueue(dict(actor_id='TUR',url=u,kind='mfa',title=title.strip(),method='official_MFA_year_category_archive'))
                elif h.startswith('javascript:'):continue
                elif t['depth']<3 and (re.fullmatch(r'[2-4]',title.strip()) or title.strip().casefold() in ('next','next >')) and u!=t['url']:
                    self.query('TUR',u,'mfa_year_archive',category=t['category'],year=t['year'],depth=t['depth']+1)
            if t['kind']=='mfa_year_archive':
                numbers=[int(x) for x in re.findall(r'Page\$(\d+)',html.unescape(raw.decode()))]
                # Four temporally spread pages, not an unrestricted site crawl.
                selected=sorted({2,4,max(numbers,default=1)//2,max(numbers,default=1)})
                for number in selected:
                    if number<=1 or number not in numbers:continue
                    self.query('TUR',t['url']+'#archive-page-'+str(number),'mfa_postback',base_url=t['url'],page_number=number,category=t['category'],year=t['year'],depth=1)
            elif t['depth']<2:
                numbers=[int(x) for x in re.findall(r'Page\$(\d+)',html.unescape(raw.decode()))]
                end=max(numbers,default=t['page_number'])
                if end>t['page_number'] and t['page_number']>=10:
                    for number in sorted({(end+t['page_number'])//2,end}):
                        if number not in numbers:continue
                        self.query('TUR',t['base_url']+'#archive-page-'+str(number),'mfa_postback',base_url=t['base_url'],page_number=number,category=t['category'],year=t['year'],depth=2,form_parent_receipt=m)
        elif t['kind']=='mea_fulltext':
            data=json.loads(raw)
            if not data.get('Success'):raise ValueError('Official full-text search did not succeed')
            for item in data.get('Results',[]):
                title=page(item.get('title','').encode())[0];description=page(item.get('description','').encode())[0]
                if item.get('manageby')!='Publications' or not re.search(r'ukrain|crimea|sevastopol|donetsk|luhansk',title+' '+description,re.I):continue
                if re.search(r'appointed|evacuation|control centres|media delegates|missing students|detained|jails',title,re.I):continue
                if not '2014-01-01'<=item.get('content_createdate','')[:10]<='2026-10-24':continue
                u=item.get('url','');pkid=str(item.get('linkid',''))
                if not u.startswith('https://www.mea.gov.in/') or not pkid.isdigit():continue
                self.enqueue(dict(actor_id='IND',url=u,kind='mea',title=title,pkid=pkid,method='official_MEA_published_fulltext_search',search_term=t['model']['searchText'],index_date=item['content_createdate'][:10]))
        elif t['kind']=='mea_listing':
            for h,title in ls:
                if 'dtl/' in h and (ANCHOR.search(title+' '+h) or t['term']=='military assistance'):
                    self.enqueue(dict(actor_id='IND',url=urljoin('https://www.mea.gov.in',h),kind='mea',title=title.strip(),pkid=re.search(r'dtl/(\d+)',h)[1],method='official_MEA_policy_keyword_listing'))
        elif t['kind']=='govza_search':
            for h,title in ls:
                if h.startswith('/news/') and re.search(r'ukrain|crimea|russia|sanction',h+' '+title,re.I):self.enqueue(dict(actor_id='ZAF',url=urljoin(t['url'],h),kind='govza',title=title.strip(),method='official_government_correct_search_form'))
        elif t['kind']=='wp':
            posts=json.loads(raw)
            if not isinstance(posts,list):raise ValueError('Not a published-post list')
            for p in posts:
                title=page(p['title']['rendered'].encode())[0]
                self.enqueue(dict(actor_id='ZAF',url=p['link'],kind='wp',title=title,post=p,bulk_receipt=m,method='official_DIRCO_gap_keyword_search'))
        elif t['kind']=='commission_search':
            data=json.loads(raw)
            for item in data.get('docuLanguageListResources',[]):
                title=item['title']
                if not re.search(r'Ukraine|Crimea|annex|Russia',title,re.I):continue
                if not re.search(r'High Representative|European Council|Michel|Costa|Van Rompuy|Tusk|Barroso|Juncker|on behalf|European Union',title,re.I):continue
                if re.search(r'joint press conference',title,re.I):continue
                ref=item['refCode'];self.enqueue(dict(actor_id='EU',url='https://ec.europa.eu/commission/presscorner/detail/en/'+ref.replace('/','_').lower(),kind='commission',title=title,index=item,method='verified_public_Commission_API_common_position_search'))
        return dict(status='ok',receipt=m,discovered_tasks=len(self.state['pending_urls'])-before,official_links=len(ls),archive_year_hint=t.get('year'),archive_category=t.get('category'),page_number=t.get('page_number'),pagination_depth=t.get('depth'))
    def discover(self,n):
        for _ in range(n):
            if not self.state['pending_queries']:break
            t=self.state['pending_queries'][0]
            try:r=self.discover_one(t)
            except Exception as e:r=dict(status='failed',reason=str(e))
            self.state['query_definitions'][t['url']]=t
            self.state['queries'][t['url']]=dict(r,actor_id=t['actor_id'],kind=t['kind']);self.state['pending_queries'].pop(0);self.save()
            if t['kind']=='mfa_postback':
                counts=self.state.setdefault('form_failures_by_archive',{});base=t['base_url']
                counts[base]=counts.get(base,0)+1 if r['status']=='failed' else 0
                if counts[base]>=2:
                    self.state.setdefault('deferred_queries',[]).extend(dict(x,deferred_reason='Two corrected public-form failures for this archive; stop this archive') for x in self.state['pending_queries'] if x.get('base_url')==base)
                    self.state['pending_queries']=[x for x in self.state['pending_queries'] if x.get('base_url')!=base]
                elif r['status']=='ok':
                    deferred=[x for x in self.state.get('deferred_queries',[]) if x.get('base_url')==base and x['url'] not in self.state['queries']]
                    if deferred:
                        nxt=max(deferred,key=lambda x:x['page_number']);self.state['pending_queries'].append(nxt);self.state['deferred_queries'].remove(nxt)
                self.save()
    def retrieve(self,t):
        if t['kind']=='commission':
            api='https://ec.europa.eu/commission/presscorner/api/documents?'+urlencode(dict(reference=t['index']['refCode'],language='en',etrans='false'))
            raw,m=self.store.get(api);document=json.loads(raw);dola=document['docuLanguageResource'];text,parser=page(dola['htmlContent'].encode())
        elif t['kind']=='mea':
            api='https://www.mea.gov.in/FrontEnd/FetchPublicationDetailData?'+urlencode(dict(pkid=t['pkid'],languageId=1))
            try:raw,m=self.store.get(api)
            except ValueError as e:
                # Same permitted URL/UA, one retry after the benchmark established
                # current endpoint availability. Old receipts stay in history.
                if 'Cached request failure' not in str(e) or '403' not in str(e):raise
                raw,m=self.store.get(api,refresh=True)
            text,parser=page(raw)
        elif t['kind']=='wp':
            raw=t['post']['content']['rendered'].encode();m=t['bulk_receipt'];text,parser=page(raw)
        else:
            raw,m=self.store.get(t['url'])
            if t['kind']=='council':
                if not raw.startswith(b'%PDF'):raise ValueError('Not PDF')
                with tempfile.TemporaryDirectory() as f:
                    p=Path(f)/'source.pdf';p.write_bytes(raw);text=normalize(subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,text=True,check=True).stdout)
                if not re.search(r'conclusions\s+adopted|as\s+approved\s+by\s+the\s+Council',text[:5000],re.I):raise ValueError('Not adopted Council common position')
                parser=None
            else:text,parser=page(raw,'main' if t['kind']=='govza' else None)
        if len(text)<200 or re.search(r'Bakım sürüyor|Alt Yapı Bakım|under maintenance|Loading\.\.\.',text,re.I):raise ValueError('Maintenance/navigation shell, not usable source text')
        if not ANCHOR.search(text):raise ValueError('No Russia-Ukraine policy/conflict anchor')
        title=t['title'];event=date_value(title);published=None;flags=[]
        if t['kind']=='commission':
            title=dola['title'];event=t['index']['eventDate'][:10];published=(document.get('publishDate') or '')[:10] or None;body_start=0
            issuer='European Union institutional statement, published by the European Commission';speaker=title
            representation=bool(re.search(r'on behalf of (?:the )?(?:European Union|EU)\b',title+' '+text,re.I))
            authority=title+' '+(dola.get('subtitle') or '')+' '+text[:1500]+' '+text[-1000:]
            joint_council=bool(re.search('joint statement',title,re.I) and re.search(r'President of (?:the )?European Council|European Council President',authority,re.I) and re.search(r'President of (?:the )?European Commission|European Commission President',authority,re.I))
            if not (representation or joint_council):flags.append('EU_common_position_review')
            if dola.get('etranslated') or t['index'].get('isETranslated'):flags.append('machine_translation_requires_language_review')
        elif t['kind']=='mea':
            title_match=re.search(r'id="hdnPageTitle" value="([^"]+)"',raw.decode())
            if title_match:title=html.unescape(title_match[1])
            published=date_value(text[:400]);event=date_value(title) or published
            body_start=text.find(title)+len(title) if title in text else 0
            speaker=next((x.strip() for x in text[body_start:].splitlines() if re.search(r'Official Spokesperson.*:|Minister.*:|Foreign Secretary.*:',x)),None) or 'Ministry of External Affairs, Government of India'
            issuer='Ministry of External Affairs, Government of India'
        elif t['kind']=='mfa':
            # The article heading is duplicated in the HTML title and body. Its
            # explicit issue date, not crawl time, defines the event.
            title=html.unescape(title)
            if not title.strip():
                mm=re.search(r'<title>(.*?)</title>',raw.decode(),re.S);title=html.unescape(mm[1]).split('/')[0].strip() if mm else ''
            event=date_value(title) or date_value(text[-6000:]);published=event
            body_start=text.find(title)+len(title) if title in text else 0
            issuer='Ministry of Foreign Affairs, Republic of Türkiye';speaker=issuer
        elif t['kind']=='govza':
            title=re.sub(r'\s+',' ',title).strip()
            meta_date=re.search(r'(?:property|name)=["\'](?:article:published_time|dcterms\.date|date)["\'][^>]*content=["\'](20\d\d-\d\d-\d\d)',raw.decode(),re.I)
            time_date=re.search(r'<time[^>]*datetime=["\'](20\d\d-\d\d-\d\d)',raw.decode(),re.I)
            published=(meta_date or time_date)[1] if (meta_date or time_date) else date_value(text[:1500])
            event=date_value(title) or published;body_start=text.find(title)+len(title) if title in text else 0
            issuer='Government of South Africa official communications';speaker=title
        elif t['kind']=='wp':
            published=t['post']['date_gmt'][:10];event=date_value(title) or published;body_start=0;issuer='Department of International Relations and Cooperation, South Africa';speaker=title
        else:
            event=date_value(text[:1800]);issuer='European Council / Council of the EU';speaker=issuer;body_start=0
        if not event or not '2014-01-01'<=event<='2026-10-24':raise ValueError('Missing/out-of-period documentary event date')
        if re.search(r'UNOFFICIAL|COURTESY TRANSLATION',text[:2500],re.I):flags.append('translation_review')
        sha=digest(text.encode());did='doc-focus2-'+digest(t['url'].encode())[:24]
        event_id='event-focus2-'+digest((t['actor_id']+':'+event+':'+re.sub(r'\W','',title.casefold())).encode())[:24]
        role='evaluation_reserved' if int(digest(('sprint-split-2026:'+event_id).encode())[:8],16)%10==0 else 'development_only'
        if (t['actor_id'],event) in self.protected:role='evaluation_reserved'
        prior=self.old_by_hash.get(sha)
        if prior:
            event_id=prior['event_id'];role=prior['event_role']
        d=dict(id=did,actor_id=t['actor_id'],actor_role='focal',issuer=issuer,speaker=speaker,speaker_basis='Dated official institutional article; individual and turn attribution gated at passage level',title=title,canonical_url=t['url'],source_type=t['kind'],source_receipt=m,event_date=event,publication_date=published,retrieved_at=m['retrieved_at'],language='en',translation_provenance='Official English institutional publication; equivalence to an uncollected original not inferred',text_sha256=sha,text_path='text/'+sha+'.txt',body_start=body_start,source_quality_flags=flags,event_id=event_id,event_role=role,acquisition_method=t['method'],acquisition_stream='targeted_training_acquisition_not_position_estimation',new_source_document=True,duplicate_of=prior['id'] if prior else None)
        if t['kind']=='commission':d.update(extraction_selector='JSON docuLanguageResource.htmlContent',original_language=document.get('originalLanguage'),is_machine_translated=bool(dola.get('etranslated')),source_scope_basis='Explicit on-behalf-of-EU formula or jointly issued Council/Commission presidential statement; other comments remain held')
        (OUT/'text').mkdir(exist_ok=True);(OUT/d['text_path']).write_text(text);write_json(OUT/'documents'/(did+'.json'),d);return d
    def batch(self,n):
        tasks=self.state['pending_urls'][:n];self.state['inflight']=tasks;self.state['pending_urls']=self.state['pending_urls'][n:];self.save()
        with ThreadPoolExecutor(max_workers=4) as pool:
            todo={pool.submit(self.retrieve,t):t for t in tasks}
            for f in as_completed(todo):
                t=todo[f]
                try:d=f.result();r=dict(status='collected',document_id=d['id'])
                except Exception as e:r=dict(status='failed_or_rejected',reason=str(e))
                self.state['done'][t['url']]=r;self.save()
        self.state['inflight']=[];self.state['batches']+=1;self.save()
        from .focal_review import prepare
        prepare() # strict queues and connected split metadata, without suggestions
        print(json.dumps(dict(batch=self.state['batches'],sources=len(self.state['done']),documents=len(list((OUT/'documents').glob('*.json'))),pending=len(self.state['pending_urls']),pending_queries=len(self.state['pending_queries']))),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--batches',type=int,default=30);p.add_argument('--batch-size',type=int,default=20);p.add_argument('--queries-per-batch',type=int,default=8);p.add_argument('--finalize',action='store_true');a=p.parse_args()
    s=Acquisition();s.plan()
    for _ in range(a.batches):
        s.discover(a.queries_per_batch)
        if s.state['pending_urls']:s.batch(a.batch_size)
        elif not s.state['pending_queries']:break
    if a.finalize:
        from .focal_review import build
        build()
        from .component_review import build as components
        components()
        from .focal_report import build as report
        report()

if __name__=='__main__':main()
