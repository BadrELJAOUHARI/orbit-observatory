"""Optional, bounded HTTP-API comparison; does not install/register MCP tools.

Requires an already authorized Firecrawl account/key and observable spare credits.
No key is printed, persisted, or embedded in an artifact. Default environment has
no key: the command records unavailability and makes zero service calls.
"""
import argparse,json,os,urllib.request
from .focal_retrieval import OUT,Store,classify_body
from .collect import write_json,utcnow
from .validation import digest

URL='https://www.mea.gov.in/response-to-queries?dtl/38308/Official_Spokespersons_response_to_media_queries_on_Reuters_report_on_diversion_of_Indian_Defence_Exports_to_Ukraine'

def run(max_calls=1):
    if not 1<=max_calls<=3:raise ValueError('Comparison cap is 1–3 pages')
    key=os.environ.get('FIRECRAWL_API_KEY')
    if not key:
        result=dict(available=False,mcp_connected=False,api_credential_configured=False,service_calls=0,paid_scrapes=0,reason='No authorized Firecrawl API credential in this cloud environment')
        write_json(OUT/'firecrawl_comparison.json',result);return result
    # Validate the source through the current robots/access policy before any
    # external scrape. CAPTCHA/maintenance/authentication are never bypassed.
    raw,receipt=Store().get(URL)
    if classify_body(raw,URL).get('diagnostic') not in (None,'loading...'):
        raise ValueError('Source challenge/maintenance: enhanced scraping prohibited')
    def api(path,payload=None):
        body=json.dumps(payload).encode() if payload else None
        req=urllib.request.Request('https://api.firecrawl.dev/'+path,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as response:return json.loads(response.read())
    quota=api('v1/team/credit-usage')
    data=quota.get('data',{});remaining=data.get('remainingCredits')
    if not isinstance(remaining,(int,float)) or remaining<max_calls:
        raise ValueError('Observable sufficient quota is required; no paid scrape attempted')
    # One known permitted JS page. The cap allows extending the benchmark later;
    # this adapter intentionally does not perform a broad paid collection run.
    result=api('v2/scrape',dict(url=URL,formats=['rawHtml'],onlyMainContent=False,timeout=30000))
    if not result.get('success'):raise ValueError('Firecrawl did not return successful retrieval')
    html=result.get('data',{}).get('rawHtml')
    if not isinstance(html,str) or len(html)<300:raise ValueError('Original rendered HTML required; rewritten Markdown is insufficient')
    sha=digest(html.encode());path=OUT/'enhanced_raw'/(sha+'.html');path.parent.mkdir(exist_ok=True);path.write_text(html)
    receipt=dict(provider='Firecrawl HTTP API (not MCP)',source_url=URL,retrieved_at=utcnow(),html_sha256=sha,html_path=str(path),source_access_receipt=receipt,quota_before=remaining,paid_scrapes=1,service_calls=2,admission='Not admitted automatically: identity, completeness and provenance require comparison')
    write_json(OUT/'firecrawl_comparison.json',receipt);return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--max-calls',type=int,default=1);a=p.parse_args();print(json.dumps(run(a.max_calls)))
