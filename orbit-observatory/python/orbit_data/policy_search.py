"""Versioned policy searches. Matching terms never assign stance labels."""
import json
from urllib.parse import urlencode
from .validation import ROOT
from .reviewed import write_immutable
from .collect import Downloader

FORMULATIONS={
 'territorial_recognition':{'supporting':['Ukraine Crimea annexation non-recognition borders'],'opposing':['Ukraine recognize annexation Crimea Russian territory'],'conditional':['Ukraine territorial integrity territorial settlement conditions']},
 'troop_withdrawal':{'supporting':['Russia withdraw all Ukrainian territory'],'opposing':['Russia troops remain Ukraine withdrawal reject'],'conditional':['Russia withdrawal security conditions ceasefire']},
 'military_assistance':{'supporting':['Ukraine military assistance provide weapons'],'opposing':['Ukraine military assistance refuse suspend weapons'],'conditional':['Ukraine weapons assistance conditions restrictions']},
 'sanctions':{'supporting':['Russia sanctions adopt maintain'],'opposing':['Russia sanctions oppose reject remove'],'conditional':['Russia sanctions lift if withdrawal']},
 'invasion_responsibility':{'supporting':['Russia responsible invasion Ukraine February 2022 aggression'],'opposing':['Russia not responsible Ukraine invasion NATO blame'],'conditional':['Ukraine invasion responsibility qualified shared attribution']}}
SCOPES={'USA':['whitehouse.gov','state.gov','obamawhitehouse.archives.gov','bidenwhitehouse.archives.gov'],
 'EU':['consilium.europa.eu','eeas.europa.eu'],'TUR':['mfa.gov.tr','tccb.gov.tr'],
 'IND':['mea.gov.in'],'ZAF':['dirco.gov.za','gov.za','thepresidency.gov.za']}

def search():
 config=dict(version='policy-searches-1.0.0',scopes=SCOPES,lenses=FORMULATIONS,
    interpretation='Supporting, opposing and conditional are query families, not labels. Retain unsuccessful queries. Domain restrictions and robots gates apply; do not bypass inaccessible hosts.',
    acquisition_stream='targeted_training_acquisition',not_representative_for_country_period_scoring=True,
    supplementary_stream='purposive_UN_general_debate_archive',
    execution_scope='Official DIRCO search prioritized for missing South African policy evidence. Other actor-domain query families are versioned plans, not claimed executed searches.')
 write_immutable(ROOT/'source_manifest/targeted-v1/searches.json',config)
 out=ROOT.parent/'.local/expansion-v4';d=Downloader(out,{'dirco.gov.za','www.dirco.gov.za'})
 outcomes=[]
 for query in ['Ukraine','Russia sanctions','Ukraine military assistance','Ukraine withdrawal annexation']:
  url='https://dirco.gov.za/wp-json/wp/v2/search?'+urlencode(dict(search=query,per_page=10))
  try:
   raw,meta=d.download(url);hits=json.loads(raw)
   outcomes.append(dict(query=query,url=url,status='ok',count=len(hits),hits=[dict(id=h['id'],title=h['title'],url=h['url']) for h in hits],retrieved_at=meta['retrieved_at'],raw_sha256=meta['raw_sha256']))
  except Exception as error:outcomes.append(dict(query=query,url=url,status='blocked',reason=str(error)))
 write_immutable(out/'search_outcomes.json',outcomes)
 print(json.dumps([dict(query=o['query'],status=o['status'],count=o.get('count')) for o in outcomes],indent=2))

if __name__=='__main__':search()
