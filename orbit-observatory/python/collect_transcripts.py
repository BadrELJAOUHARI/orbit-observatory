"""Collect public-domain US presidential transcripts from official archives."""
import json, urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.skip+=1
  if tag in ('p','br','h1','h2','div'):self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.skip=max(0,self.skip-1)
  if tag=='p':self.parts.append('\n')
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
for d in json.loads((ROOT/'dist/data.json').read_text()):
 if d['id'] not in ('us2014','us2022'):continue
 try:
  req=urllib.request.Request(d['url'],headers={'User-Agent':'ORBIT portfolio research prototype'})
  raw=urllib.request.urlopen(req,timeout=25).read().decode();p=Text();p.feed(raw)
  text='\n'.join(x.strip() for x in ''.join(p.parts).splitlines() if x.strip())
  start=text.find('PRESIDENT OBAMA:') if d['id']=='us2014' else text.find('THE PRESIDENT:')
  end=text.find('\nEND',start)
  if start<0 or end<0:raise ValueError('Transcript boundaries not located')
  text=text[start:end]
  if d['quote'] not in text:raise ValueError('Evidence quote absent from transcript')
  (ROOT/'data'/f"{d['id']}.txt").write_text(text)
  print(d['id'],len(text),'characters; evidence verified')
 except Exception as e:print(d['id'],'unavailable:',e)
