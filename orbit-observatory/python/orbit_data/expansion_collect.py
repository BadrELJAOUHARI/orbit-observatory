"""Bounded official UN-source expansion with pre-reserved event clusters."""
import io,json,re,subprocess,tempfile,shutil
from pathlib import Path
from collections import Counter
from datetime import datetime
from urllib.parse import urljoin,urlsplit
from pypdf import PdfReader
from .collect import Downloader,write_json
from .text import PageText,normalize
from .validation import ROOT,digest
from .reviewed import write_immutable

OUT=ROOT.parent/'.local/expansion-v2'
ACTORS={'USA':('United States of America','united-states-america'),
        'EU':('European Union','european-union'),'TUR':('Türkiye','t%C3%BCrkiye'),
        'IND':('India','india'),'ZAF':('South Africa','south-africa'),
        'RUS':('Russian Federation','russian-federation'),'UKR':('Ukraine','ukraine')}
YEARS=[2014,2015,2016,2018,2020,2021,2024,2025]
ALIASES={'USA':['United States of America','United States'],'EU':['European Union'],
         'TUR':['Türkiye','Turkey'],'IND':['India'],'ZAF':['South Africa'],
         'RUS':['Russian Federation'],'UKR':['Ukraine']}


def plan():
    targets=[]
    for actor,(name,slug) in ACTORS.items():
        years=YEARS+[2017,2019] if actor in ('USA','EU','TUR','IND','ZAF') else [2022,2024]
        for year in years:
            session=year-1945
            targets.append(dict(document_id=f'doc-exp-{actor.lower()}-unga{session}',event_id=f'event-exp-{actor.lower()}-unga{session}',
                actor_id=actor,actor_role='focal' if actor in ('USA','EU','TUR','IND','ZAF') else 'auxiliary_training_only',
                year=year,session=session,url=f'https://gadebate.un.org/en/{session}/{slug}',
                source_type='official_delegation_full_statement_UN_archive',fallback=year in (2017,2019)))
    roles={}
    for actor in ('USA','EU','TUR','IND','ZAF'):
        pool=[t for t in targets if t['actor_id']==actor and not t['fallback']]
        ordered=sorted(pool,key=lambda t:digest(('reserve-before-content-20261023:'+t['event_id']).encode()))
        held={t['event_id'] for t in ordered[:2]}
        for t in targets:
            if t['actor_id']==actor:roles[t['event_id']]='evaluation_reserved' if t['event_id'] in held else 'development_only'
    for t in targets:
        if t['actor_role']=='auxiliary_training_only':roles[t['event_id']]='auxiliary_development_only'
    manifest=dict(version='expansion-targets-1.0.0',goal_focal_distinct_events=40,years=YEARS,
        policy='Eight additional distinct UN speech events per focal actor; explicit fallback years only if needed. Primary speeches, never AI transcripts or summaries. This purposive archive expansion is not representative coverage.',
        targets=targets)
    split=dict(version='expansion-event-split-1.0.0',seed='reserve-before-content-20261023',event_roles=roles,
        evaluation_reserved_event_ids=sorted(e for e,r in roles.items() if r=='evaluation_reserved'),
        reserved_before_collection_and_suggestions=True,translation_copy_policy='All languages and mirrored copies share the planned event ID and split. Never label reserved events with AI.',
        final_evaluation_labels_ready=False,prior_pilot_event_ids_excluded=True)
    write_immutable(ROOT/'source_manifest/expansion-v1/targets.json',manifest)
    write_immutable(ROOT/'workflow/expansion-v1/event_split.json',split)
    return manifest,split


def landing_metadata(raw,url,actor):
    parser=PageText();parser.feed(raw.decode('utf-8',errors='strict'))
    text=normalize(''.join(parser.parts))
    position=text.find('Statement\n')
    if position<0:raise ValueError('Missing official delegation heading')
    header=text[position+len('Statement\n'):].split('Kaltura')[0].split('Transcript (AI generated)')[0].split('Statement summary')[0]
    lines=header.splitlines()
    if not any(lines[0].rstrip('*').casefold()==a.casefold() for a in ALIASES[actor]):raise ValueError('Delegation identity mismatch: '+lines[0])
    match=re.search(r'\b(\d{1,2} [A-Z][a-z]+ 20\d\d)\b',header)
    if not match:raise ValueError('No verified delivery date in official metadata heading')
    date=datetime.strptime(match.group(),'%d %B %Y').date().isoformat()
    role_lines=[line for line in lines[1:] if line not in ('His Excellency','Her Excellency','H.E.','Mr.','Ms.') and not re.fullmatch(r'\d{1,2} [A-Z][a-z]+ 20\d\d',line)]
    links={}
    for href,lang,title in parser.links:
        full=urljoin(url,href)
        if urlsplit(full).hostname not in ('gadebate.un.org','gadebatestatements.un.org') or not urlsplit(full).path.lower().endswith('.pdf'):continue
        for code,name in [('en','english'),('fr','french'),('ru','russian')]:
            if lang==code or name in title.casefold() or re.search(r'[_/-]'+code+r'(?:_\d+)?\.pdf$',urlsplit(full).path,re.I):
                links.setdefault(code,set()).add(full)
    floor={urljoin(url,h) for h,l,t in parser.links if re.search(r'_fl\.pdf$',h,re.I)}
    language=next((code for code in ('en','fr','ru') if len(links.get(code,[]))==1),None)
    if language is None and len(floor)==1:
        language='floor';links['floor']=floor
    if language is None:raise ValueError('No unique official full statement attachment')
    return dict(delegation=lines[0],speaker=role_lines[0] if role_lines else None,
        speaker_role=' / '.join(role_lines[1:]),event_date=date,metadata_heading=header,
        language=language,pdf_url=next(iter(links[language])))


def extract_pdf(pdf,pages,language):
    """Preserve the first extraction; OCR is a separately flagged replacement view."""
    original=normalize('\n'.join(pages));history=[];issues=[]
    bad=len(original)<200 or len(re.findall(r'/\d+|/i255',original))>200
    if not bad:return original,history,issues
    sha=digest(original.encode());path='text/'+sha+'.txt'
    (OUT/'text').mkdir(exist_ok=True);(OUT/path).write_text(original,encoding='utf-8')
    history.append(dict(extractor='pypdf',text_path=path,text_sha256=sha,status='unusable_font_mapping_or_image_only'))
    if language not in ('en','floor'):raise ValueError('OCR language model unavailable for original language')
    with tempfile.TemporaryDirectory(prefix='orbit-ocr-') as folder:
        source=Path(folder)/'source.pdf';source.write_bytes(pdf)
        subprocess.run(['pdftoppm','-scale-to','2200','-png',str(source),str(Path(folder)/'page')],check=True,capture_output=True)
        texts=[]
        for page in sorted(Path(folder).glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1])):
            texts.append(subprocess.run(['tesseract',str(page),'stdout','-l','eng'],check=True,capture_output=True,text=True).stdout)
        text=normalize('\n'.join(texts))
    if len(text)<200:raise ValueError('OCR failed to recover usable text')
    issues.append('OCR_text_requires_visual_review')
    history.append(dict(extractor='pdftoppm-2200+tesseract-eng',status='recovered_pending_visual_review',original_text_sha256=sha))
    return text,history,issues


def collect():
    manifest,split=plan();OUT.mkdir(parents=True,exist_ok=True)
    extra=ROOT/'source_manifest/expansion-v1/supplement.json'
    if extra.exists():
        supplement=json.loads(extra.read_text());manifest=dict(manifest,targets=manifest['targets']+supplement['targets']);split=dict(split,event_roles={**split['event_roles'],**supplement['event_roles']})
    for name in ('cache','raw'):
        prior=ROOT.parent/'.local/expansion-v1'/name
        if prior.exists():shutil.copytree(prior,OUT/name,dirs_exist_ok=True)
    downloader=Downloader(OUT,{'gadebate.un.org','gadebatestatements.un.org'})
    catalog=[];outcomes=[];success=Counter()
    for target in manifest['targets']:
        actor=target['actor_id']
        if target['fallback'] and success[actor]>=8:
            outcomes.append(dict(**target,status='not_needed',reason='Eight primary events already collected'));continue
        item_path=OUT/'items'/(target['document_id']+'.json')
        try:
            if item_path.exists():
                document=json.loads(item_path.read_text())
                for path,sha in [(document['raw_path'],document['raw_sha256']),(document['text_path'],document['text_sha256'])]:
                    if digest((OUT/path).read_bytes())!=sha:raise ValueError('Cached source hash mismatch')
            else:
                raw,landing=downloader.download(target['url'])
                if landing['content_type'] not in ('text/html','application/xhtml+xml'):raise ValueError('UN landing page is not HTML')
                meta=landing_metadata(raw,landing['resolved_url'],actor)
                if not meta['event_date'].startswith(str(target['year'])):raise ValueError('Landing date does not match planned event year')
                pdf,download=downloader.download(meta['pdf_url'])
                if not pdf.startswith(b'%PDF-'):raise ValueError('Attachment is not a PDF')
                reader=PdfReader(io.BytesIO(pdf));pages=[p.extract_text() or '' for p in reader.pages]
                text,extraction_history,extraction_issues=extract_pdf(pdf,pages,meta['language'])
                language=meta['language'];issues=list(extraction_issues)
                if language=='floor':
                    language='fr' if re.search(r'(?i)mesdames|monsieur|européenne',text[:5000]) else 'und'
                    issues.append('language_review')
                if language=='fr':issues.append('language_review')
                upper=text[:2200].upper()
                if 'UNOFFICIAL TRANSLATION' in upper:translation='Explicitly marked UNOFFICIAL TRANSLATION; original-language version not collected.';issues.append('translation_review')
                elif 'COURTESY TRANSLATION' in upper:translation='Explicitly marked Courtesy Translation; original-language version not collected.';issues.append('translation_review')
                elif actor in ('TUR','RUS','UKR'):
                    translation='Delegation-published English/French version in UN archive; original-language equivalence and translator not verified.';issues.append('translation_review')
                else:translation=None
                if re.search(r'(?i)English Rendition|unofficial|courtesy translation',text[:2200]):
                    issues.append('translation_review');translation=translation or 'Delegation attachment marked English Rendition; original-language equivalence not verified.'
                if actor=='EU' and re.search(r'(?i)Monsieur|Mesdames',text[:1200]):
                    language='fr';issues.append('language_review')
                if actor=='RUS':issues.append('language_review')
                institutional='institutional_role_verified_no_common_position_clearance' if actor=='EU' else 'official_delegation_role_verified_pending_passage_review'
                if actor=='EU':
                    if re.search(r'(?i)on behalf of (?:the )?European Union|au nom de l.Union europ',text):institutional='explicit_EU_representation_formula_verified'
                    else:issues.append('EU_common_position_review')
                text_hash=digest(text.encode());text_path='text/'+text_hash+'.txt'
                (OUT/'text').mkdir(exist_ok=True);(OUT/text_path).write_text(text,encoding='utf-8')
                document=dict(**target,record_type='expansion_document',schema_version='1.0.0',**meta,
                    event_role=split['event_roles'][target['event_id']],canonical_url=landing['resolved_url'],resolved_url=download['resolved_url'],
                    issuer=meta['speaker']+' / '+meta['speaker_role'],publisher='UN General Debate official delegation archive',
                    publication_date=None,date_basis='Delivery date verified from official landing heading; publication date unavailable, not inferred.',
                    retrieved_at=download['retrieved_at'],landing_retrieved_at=landing['retrieved_at'],raw_path=download['raw_path'],raw_sha256=download['raw_sha256'],
                    landing_raw_path=landing['raw_path'],landing_raw_sha256=landing['raw_sha256'],text_path=text_path,text_sha256=text_hash,
                    normalization_version='orbit-text-v1',extraction_history=extraction_history,pages=len(pages),translation_provenance=translation,
                    institutional_scope_status=institutional,quality_issues=issues,
                    rights_status='private_research_cache_not_cleared_for_public_redistribution',
                    duplicate_of=None,translation_of=None)
                write_immutable(item_path,document)
            catalog.append(document);success[actor]+=1
            outcomes.append(dict(document_id=target['document_id'],event_id=target['event_id'],actor_id=actor,status='collected'))
            print(f"COLLECTED {actor} {target['year']} {document['language']} {document['event_date']} {len((OUT/document['text_path']).read_text())} chars",flush=True)
        except Exception as error:
            outcomes.append(dict(**target,status='blocked',reason=str(error)))
            print('BLOCKED',actor,target['year'],type(error).__name__,str(error)[:160],flush=True)
        write_json(OUT/'catalog.json',catalog);write_json(OUT/'outcomes.json',outcomes)
    # Exact source copies cannot create extra events, even if a landing page is mislabeled.
    seen={}
    for doc in sorted(catalog,key=lambda d:(d['year'],d['actor_id'])):
        k=(doc['actor_id'],doc['text_sha256'])
        if k in seen:
            doc['duplicate_of']=seen[k];doc['quality_issues'].append('cross_year_attachment_conflict')
        else:seen[k]=doc['document_id']
    write_json(OUT/'catalog.json',catalog);write_json(OUT/'outcomes.json',outcomes)
    report=dict(target_focal_events=40,collected_focal_distinct_events=sum(d['actor_role']=='focal' and not d['duplicate_of'] for d in catalog),
        collected_auxiliary_distinct_events=sum(d['actor_role']=='auxiliary_training_only' and not d['duplicate_of'] for d in catalog),
        by_actor=dict(Counter(d['actor_id'] for d in catalog if not d['duplicate_of'])),
        blocked=[o for o in outcomes if o['status']=='blocked'],event_split_reserved_before_content=True,
        source_types='UN delegation full speeches only. No press summaries or AI transcripts used as evidence.',
        coverage_limit='Archive speeches may lack relevant stance; targeted passage coverage and class balance must be reported separately.')
    write_json(OUT/'collection_report.json',report)
    write_immutable(ROOT/'data/expansion-v2/collection_report.json',report)
    print('REPORT',json.dumps({k:v for k,v in report.items() if k!='blocked'}),flush=True)

if __name__=='__main__':collect()
