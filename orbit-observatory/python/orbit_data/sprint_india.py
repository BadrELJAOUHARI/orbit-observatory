"""MEA's own documented public listing/detail endpoints; separate resumable batch state."""
import argparse,json,re
from urllib.parse import urlencode,urljoin
from . import acquisition_sprint as core
from .validation import ROOT
from .collect import write_json
from .text import PageText

def main():
 core.OUT=ROOT.parent/'.local/acquisition-india-v1';s=core.Sprint()
 for keyword in ['Ukraine','Crimea','Russian invasion']:
  for page in range(1,5):
   u='https://www.mea.gov.in/FrontEnd/FetchPublicationListingData?'+urlencode(dict(publicationId=0,KeywordName=keyword,SortBy='desc',page=page,PageSize=100,DateRange='',IsInternalMEA='false',PLngId=1))
   def handler(raw,meta):
    text=raw.decode();n=0
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']*dtl/(\d+)[^"\']*)["\'][^>]*>(.*?)</a>',text,re.S):
     title=core.parse_html(m[3]);prefix=core.parse_html(text[max(0,m.start()-1400):m.start()]);dates=re.findall(r'\d{1,2}\s+(?:'+core.MONTHS.replace('','') .replace(' ','|')+r'),?\s+20\d\d',prefix)
     date=core.date_title(dates[-1].replace(',','') if dates else title,None)
     if not date:continue
     s.enqueue(dict(url=urljoin('https://www.mea.gov.in',m[1]),actor_id='IND',issuer='Ministry of External Affairs, Government of India',kind='mea',title=title,event_date=date,pkid=m[2],method='documented_MEA_public_listing_keyword_endpoint'));n+=1
    return n
   s.query(u,handler)
 for _ in range(30):
  if not s.state['pending']:break
  s.process(25)
if __name__=='__main__':main()
