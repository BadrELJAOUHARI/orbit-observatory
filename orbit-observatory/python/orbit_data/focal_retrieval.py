"""Cached, rate-limited official retrieval for the second acquisition increment."""
import json,re,threading,time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit,urljoin,urlunsplit,quote
from collections import defaultdict
from .collect import Downloader,write_json,USER_AGENT,utcnow
from .validation import ROOT,digest
from .text import PageText,normalize

OUT=ROOT.parent/'.local/focal-acquisition-v2'
OLD=ROOT.parent/'.local/acquisition-sprint-v1'
LOCKS=defaultdict(threading.Lock)

def wire_url(url):
    """Percent-encode Unicode URL characters without changing the source URL."""
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe='/%:@'),quote(p.query,safe='=&%+/:?@'),p.fragment))

def historical_metadata():
    """All prior source/split metadata, never historical reserved source text."""
    docs=json.loads((OLD/'source_event_manifest.json').read_text())
    split=json.loads((ROOT.parent/'.local/experimental-baseline-v2/leakage_groups.json').read_text())
    for name in ['pilot-v1/records.json','expansion-v6/cleared_catalog.json']:
        for d in json.loads((ROOT.parent/'.local'/name).read_text()):
            if d.get('record_type') not in ('document','expansion_document'):continue
            g=split['event_groups'].get(d['event_id']);role='evaluation_reserved' if g in split['reserved_leakage_group_ids'] else 'development_only'
            docs.append(dict(d,id=d.get('id',d.get('document_id')),event_date=d.get('event_date',d.get('delivery_date')),canonical_url=d.get('canonical_url',d.get('url')),leakage_group_id=g or d['event_id'],event_role=role))
    return docs

class Store:
    def __init__(self):
        OUT.mkdir(exist_ok=True,parents=True);self.clients={};self.calls=0;self.cache_hits=0
        self.priors=[OLD,ROOT.parent/'.local/expansion-v6',ROOT.parent/'.local/expansion-v5',ROOT.parent/'.local/source-clearance-20261024']
        self.priors += [p.parent for p in (ROOT.parent/'.local').glob('*/cache') if p.parent!=OUT and p.parent not in self.priors]
    def reuse(self,url,success_only=False):
        key=digest(url.encode())+'.json'
        if (OUT/'cache'/key).exists():return
        for base in self.priors:
            path=base/'cache'/key
            if not path.exists():continue
            meta=json.loads(path.read_text())
            if success_only and meta.get('status')!='ok':continue
            if meta.get('status')=='ok':
                raw=(base/meta['raw_path']).read_bytes()
                if digest(raw)!=meta['raw_sha256']:raise ValueError('Prior cache hash mismatch')
                target=OUT/meta['raw_path'];target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(raw)
            write_json(OUT/'cache'/key,meta);return
    def get(self,url,refresh=False):
        url=wire_url(url)
        host=urlsplit(url).hostname
        restrictions=OUT/'source_restrictions.json'
        if restrictions.exists() and host in json.loads(restrictions.read_text()) and not url.endswith('/robots.txt'):
            raise ValueError('Documented source AI-input/training restriction; acquisition held')
        if not host or not (host.endswith('.gov.in') or host.endswith('.gov.tr') or host.endswith('.gov.za') or host in ['dirco.gov.za','gadebate.un.org','gadebatestatements.un.org','data.consilium.europa.eu','www.consilium.europa.eu','home.treasury.gov','www.gov.uk','pminewyork.gov.in','mea.gov.in','presidency.gov.za','www.thepresidency.gov.za','www.dfa.gov.za','2021-2025.state.gov','osce.usmission.gov','ec.europa.eu']):raise ValueError('Unverified official host '+str(host))
        with LOCKS[host]:
            if host not in self.clients:self.clients[host]=Downloader(OUT,{host},interval=1.1,accept_header='text/html,application/pdf,application/json,text/plain')
            self.reuse('https://'+host+'/robots.txt',success_only=True)
            if not refresh:self.reuse(url)
            cache=OUT/'cache'/(digest(url.encode())+'.json')
            if cache.exists() and not refresh:self.cache_hits+=1
            else:self.calls+=1
            client=self.clients[host]
            client.check_robots(url)
            rp=OUT/'cache'/(digest(('https://'+host+'/robots.txt').encode())+'.json')
            if rp.exists():
                rm=json.loads(rp.read_text())
                if rm.get('status')=='ok':
                    policy=(OUT/rm['raw_path']).read_text()
                    if re.search(r'ai-(?:input|train)\s*=\s*no',policy,re.I) and not url.endswith('/robots.txt'):
                        existing=json.loads(restrictions.read_text()) if restrictions.exists() else {}
                        existing[host]=dict(policy_url='https://'+host+'/robots.txt',source_receipt=rm,directives=re.findall(r'ai-(?:input|train)\s*=\s*no',policy,re.I),disposition='Source rights hold; no AI preparation/training collection')
                        write_json(restrictions,existing)
                        raise ValueError('Documented source AI-input/training restriction; acquisition held')
            if not refresh:return client.fetch(url)
            # One authorized benchmark retry, without bypassing current robots.
            if cache.exists():write_json(OUT/'receipt_history'/(digest(cache.read_bytes())+'.json'),json.loads(cache.read_text()))
            client.refresh=True
            try:return client.fetch(url)
            finally:client.refresh=False
    def public_form(self,url,fields,browser_headers=True):
        """Public ASP.NET archive pagination, preserving request hash and receipt."""
        from urllib.parse import urlencode
        payload=urlencode(fields).encode();key=digest(url.encode()+(b'\0POST-SAME-ORIGIN\0' if browser_headers else b'\0POST\0')+payload);cache=OUT/'cache'/(key+'.json');host=urlsplit(url).hostname
        if cache.exists():
            m=json.loads(cache.read_text())
            if m['status']!='ok':raise ValueError('Cached public-form failure: '+m['error'])
            raw=(OUT/m['raw_path']).read_bytes()
            if digest(raw)!=m['raw_sha256']:raise ValueError('Form cache hash mismatch')
            return raw,m
        self.get(url) # verifies official host/robots; reuses the initial GET
        with LOCKS[host]:
            client=self.clients[host];client.check_robots(url)
            wait=client.interval-(time.monotonic()-client.last_request.get(host,0))
            if wait>0:time.sleep(wait)
            client.last_request[host]=time.monotonic()
            try:
                headers={'User-Agent':USER_AGENT,'Content-Type':'application/x-www-form-urlencoded'}
                if browser_headers:headers.update(Origin='https://'+host,Referer=url)
                req=urllib.request.Request(url,data=payload,headers=headers)
                with client.opener.open(req,timeout=25) as response:
                    raw=response.read(20_000_001)
                    if len(raw)>20_000_000:raise ValueError('Archive response exceeds cap')
                    m=dict(status='ok',requested_url=url,resolved_url=response.url,retrieved_at=utcnow(),content_type=response.headers.get_content_type(),raw_sha256=digest(raw),http_method='POST',request_body_sha256=digest(payload),request_purpose='published archive pagination, no authentication')
                m['raw_path']='raw/'+m['raw_sha256']+'.bin';p=OUT/m['raw_path'];p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(raw);write_json(cache,m);return raw,m
            except Exception as e:write_json(cache,dict(status='error',requested_url=url,error=str(e),request_body_sha256=digest(payload)));raise

    def public_json(self,url,model):
        """The public MEA search UI's JSON POST, not a private search service."""
        payload=json.dumps(model,sort_keys=True).encode();key=digest(url.encode()+b'\0PUBLIC-JSON\0'+payload)
        cache=OUT/'cache'/(key+'.json');host=urlsplit(url).hostname
        if cache.exists():
            m=json.loads(cache.read_text())
            if m['status']!='ok':raise ValueError('Cached public-search failure: '+m['error'])
            raw=(OUT/m['raw_path']).read_bytes()
            if digest(raw)!=m['raw_sha256']:raise ValueError('Search cache hash mismatch')
            return raw,m
        self.get('https://'+host+'/advanced-search-list')
        with LOCKS[host]:
            client=self.clients[host];client.check_robots(url)
            wait=client.interval-(time.monotonic()-client.last_request.get(host,0))
            if wait>0:time.sleep(wait)
            client.last_request[host]=time.monotonic()
            try:
                req=urllib.request.Request(url,data=payload,headers={'User-Agent':USER_AGENT,'Content-Type':'application/json; charset=utf-8','Accept':'application/json','Origin':'https://'+host,'Referer':'https://'+host+'/advanced-search-list'})
                with client.opener.open(req,timeout=30) as response:
                    raw=response.read(10_000_001)
                    if len(raw)>10_000_000:raise ValueError('Search response exceeds cap')
                    m=dict(status='ok',requested_url=url,resolved_url=response.url,retrieved_at=utcnow(),content_type=response.headers.get_content_type(),raw_sha256=digest(raw),http_method='POST',request_body_sha256=digest(payload),request_purpose='Published anonymous full-text search API; no authentication')
                m['raw_path']='raw/'+m['raw_sha256']+'.bin';(OUT/m['raw_path']).write_bytes(raw);write_json(cache,m);return raw,m
            except Exception as e:write_json(cache,dict(status='error',requested_url=url,error=str(e),request_body_sha256=digest(payload)));raise

def page(raw,root=None):
    p=PageText(root);p.feed(raw.decode('utf-8',errors='strict'));return normalize(''.join(p.parts)),p

def classify_body(raw,url):
    if raw.startswith(b'%PDF'):return dict(kind='pdf_requires_extraction',full_text=False,chars=0)
    text,p=page(raw);lo=text.casefold()
    bad=next((s for s in ['under maintenance','site is under maintenance','access denied','verify you are human','captcha','loading...'] if s in lo),None)
    relevant=bool(re.search(r'ukrain|crimea|sevastopol|donetsk|luhansk|ukrayna|kırım',text,re.I))
    full=len(text)>500 and relevant and not (bad and len(text)<2500)
    return dict(kind='full_text_candidate' if full else ('maintenance_challenge_or_shell' if bad else 'index_or_unverified_document'),full_text=full,chars=len(text),diagnostic=bad,links=len(p.links))

def render_permitted(store,url):
    """TLS-verified HTTP relay to Chromium, keeping robots and source receipts.

    Only the original official origin is allowed. No TLS validation is disabled,
    no UA spoofing, and blocked responses are not retried through a new service.
    """
    from playwright.sync_api import sync_playwright
    start=time.monotonic();host=urlsplit(url).hostname;receipts=[];errors=[]
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        c=b.new_context(user_agent=USER_AGENT);pg=c.new_page()
        def route(r):
            if urlsplit(r.request.url).hostname!=host or r.request.resource_type in ('image','font','media') or len(receipts)+len(errors)>=24:
                r.abort();return
            try:
                body,meta=store.get(r.request.url);receipts.append(meta)
                r.fulfill(status=200,body=body,content_type=meta['content_type'])
            except Exception as e:errors.append(dict(url=r.request.url,reason=str(e)));r.abort()
        c.route('**/*',route)
        try:
            pg.goto(url,wait_until='domcontentloaded',timeout=30000);pg.wait_for_timeout(2500)
            dom=pg.content();text=pg.locator('body').inner_text()
            sha=digest(dom.encode());path=OUT/'rendered'/(sha+'.html');path.parent.mkdir(exist_ok=True);path.write_text(dom)
            result=dict(chars=len(text),full_text=bool(re.search(r'ukrain|ukrayna',text,re.I)) and len(text)>600 and 'Loading...' not in text,rendered_dom_path=str(path),rendered_sha256=sha)
        except Exception as e:result=dict(full_text=False,error=str(e))
        b.close()
    return dict(result,method='Chromium with same-origin TLS-verified robots-respecting HTTP relay',elapsed_seconds=round(time.monotonic()-start,3),resource_receipts=receipts,resource_errors=errors)

BENCHMARK=[
 ('IND','detail_access','https://www.mea.gov.in/FrontEnd/FetchPublicationDetailData?pkid=41740&languageId=1'),
 ('IND','JS_shell','https://www.mea.gov.in/response-to-queries?dtl/38308/Official_Spokespersons_response_to_media_queries_on_Reuters_report_on_diversion_of_Indian_Defence_Exports_to_Ukraine'),
 ('IND','detail_extraction','https://www.mea.gov.in/FrontEnd/FetchPublicationDetailData?pkid=38308&languageId=1'),
 ('IND','speaker_attribution','https://www.mea.gov.in/FrontEnd/FetchPublicationDetailData?pkid=34899&languageId=1'),
 ('IND','discovery_pagination','https://www.mea.gov.in/FrontEnd/FetchPublicationListingData?publicationId=0&KeywordName=Ukraine&SortBy=desc&page=2&PageSize=100&DateRange=&IsInternalMEA=false&PLngId=1'),
 ('IND','mission_discovery','https://pminewyork.gov.in/IndiaatUNGA'),
 ('TUR','wrong_index_maintenance','https://www.mfa.gov.tr/sitemap.xml'),
 ('TUR','correct_index_discovery','https://www.mfa.gov.tr/default.en.mfa'),
 ('TUR','presidency_discovery','https://www.tccb.gov.tr/en/speeches-statements/'),
 ('TUR','ministry_archive_discovery','https://www.mfa.gov.tr/sub.en.mfa?7cafe2ef-78bd-4d88-b326-3916451364f3'),
 ('ZAF','previous_timeout','https://dirco.gov.za/wp-json/wp/v2/posts?search=Russia&per_page=50&page=1'),
 ('ZAF','presidency_discovery','https://www.thepresidency.gov.za/search?search_api_fulltext=Ukraine'),
 ('ZAF','government_discovery','https://www.gov.za/search?search_api_fulltext=Ukraine')]

def benchmark():
    from concurrent.futures import ThreadPoolExecutor,as_completed
    store=Store();target=OUT/'benchmark.json'
    if target.exists():return json.loads(target.read_text())
    results=[]
    def one(t):
        actor,issue,url=t;start=time.monotonic();r=dict(actor=actor,prior_problem=issue,url=url)
        try:
            store.reuse(url);path=OUT/'cache'/(digest(url.encode())+'.json')
            r['prior_cached_result']=json.loads(path.read_text()).get('status') if path.exists() else 'not_cached'
            raw,meta=store.get(url,refresh=r['prior_cached_result']=='error');r.update(receipt=meta,**classify_body(raw,url))
            text,p=page(raw);r['discovered_official_policy_links']=[urljoin(url,h) for h,l,tt in p.links if re.search(r'ukrain|crimea|ukrayna|kirim|kırım|russ',h+' '+tt,re.I)][:30]
        except Exception as e:r.update(full_text=False,stage='network_or_robots_access',reason=str(e))
        r['elapsed_seconds']=round(time.monotonic()-start,3);return r
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(one,t) for t in BENCHMARK]):results.append(f.result());write_json(OUT/'benchmark-inflight.json',results)
    for r in results:
        if r.get('receipt') and r.get('kind')=='maintenance_challenge_or_shell' and r['prior_problem']=='JS_shell':r['browser_comparison']=render_permitted(store,r['url'])
    result=dict(version='retrieval-benchmark-2.0.0',urls=len(results),results=results,http_calls=store.calls,cache_hits=store.cache_hits,firecrawl_available=False,firecrawl_credentials_configured=False,external_service_calls=0,cost='No paid service used; local HTTP/browser cost not observable',capabilities=dict(web_search_tool=False,http='urllib with verified TLS/robots/caching',browser='Chromium/Playwright; same-origin HTTP relay available',pdf='pypdf/poppler',ocr_languages=['eng','osd']))
    write_json(target,result);return result

if __name__=='__main__':
    b=benchmark();print(json.dumps(dict(urls=b['urls'],full_text_candidates=sum(r.get('full_text',False) for r in b['results']),calls=b['http_calls'],cache_hits=b['cache_hits'])))
