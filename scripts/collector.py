"""Public-source collection. Detects changes; never makes legal/AI decisions.

Only official public sources are fetched. On failure the last good source state
is retained. Reviewed findings and private mail/review records are never written.
"""
from __future__ import annotations
import argparse, copy, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KST=timezone(timedelta(hours=9))
COMPANIES={'ckd':('종근당','00992871'),'hold':('종근당홀딩스','00149354'),'kb':('경보제약','00101664')}
BOARDS={'general':('기업공시제도 일반','https://dart.fss.or.kr/info/searchGuide.do','selectGuide.do'),
        'caution':('공시유의사항','https://dart.fss.or.kr/info/searchGuide02.do','selectGuide1.do')}
ALLOWED={'dart.fss.or.kr','www.fss.or.kr','www.fsc.go.kr','opendart.fss.or.kr'}
class CollectionError(Exception):pass

class Plain(HTMLParser):
 def __init__(self):super().__init__();self.out=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.skip+=1
  if tag in ('tr','br','p','div','li'):self.out.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.skip=max(0,self.skip-1)
  if tag in ('td','th'):self.out.append(' | ')
 def handle_data(self,data):
  if not self.skip:self.out.append(data)
def plain(value):
 p=Plain();p.feed(value);return '\n'.join(re.sub(r'\s+',' ',x).strip() for x in ''.join(p.out).splitlines() if x.strip())
def digest(value):return hashlib.sha256(value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def validate_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or p.hostname not in ALLOWED or p.username or p.password or p.port not in (None,443):raise CollectionError('official_url_rejected')
 return url
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  validate_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,limit=24*1024*1024):
 validate_url(url)
 for attempt in range(2):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (DisclosureDesk public source check)'})
   with urllib.request.build_opener(Redirect()).open(req,timeout=25) as r:
    validate_url(r.url);raw=r.read(limit+1)
   if len(raw)>limit:raise CollectionError('response_too_large')
   return raw
  except Exception:
   if attempt==1:raise CollectionError('official_source_unavailable') from None
   time.sleep(1)
def decode(raw):
 for encoding in ('utf-8','cp949'):
  try:return raw.decode(encoding)
  except UnicodeDecodeError:pass
 raise CollectionError('encoding_unrecognized')
def parse_filings(text,company,corp_code,start,end):
 m=re.search(r'총\s*([\d,]+)\s*건',text)
 if not m:raise CollectionError('filing_count_missing')
 total=int(m[1].replace(',',''));rows=[]
 for row in re.findall(r'<tr[^>]*>(.*?)</tr>',text,re.S):
  receipt=re.search(r'id="r_(\d{14})"',row)
  if not receipt:continue
  code=re.search(r"openCorpInfoNew\('(\d{8})'",row)
  if not code or code[1]!=corp_code:raise CollectionError('company_identity_mismatch')
  cells=re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)
  if len(cells)<6:raise CollectionError('filing_columns_changed')
  date=plain(cells[4]).replace('.','-')
  if not start<=date<=end:raise CollectionError('filing_date_outside_range')
  rows.append(dict(company_id=company,corp_code=corp_code,receipt_no=receipt[1],title=re.sub(r'\s+',' ',plain(cells[2])),filer=plain(cells[3]),received_date=date,remarks=plain(cells[5]),url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+receipt[1]))
 if len({r['receipt_no'] for r in rows})!=len(rows):raise CollectionError('duplicate_receipts_on_page')
 if total and not rows:raise CollectionError('filing_rows_missing')
 return rows,total
def collect_filings(company,start,end,request=fetch):
 name,code=COMPANIES[company];all_rows=[];total=None;pages=0;hashes=[]
 for page in range(1,31):
  url='https://dart.fss.or.kr/dsab001/search.ax?'+urllib.parse.urlencode(dict(currentPage=page,maxResults=100,maxLinks=10,sort='date',series='desc',textCrpCik=code,textCrpNm='',startDate=start.replace('-',''),endDate=end.replace('-',''),finalReport='',businessCode='all'))
  raw=request(url);rows,count=parse_filings(decode(raw),company,code,start,end);hashes.append(digest(raw));pages+=1
  if total is None:total=count
  if count!=total:raise CollectionError('filing_count_changed_during_pagination')
  all_rows+=rows
  if len(all_rows)>=total:break
 if len(all_rows)!=total or len({r['receipt_no'] for r in all_rows})!=total:raise CollectionError('filing_pages_incomplete')
 return all_rows,dict(total=total,pages=pages,response_hashes=hashes,from_date=start,to_date=end,mode='public_search')
def parse_board(text,key):
 result=[]
 for row in re.findall(r'<tr[^>]*>(.*?)</tr>',text,re.S):
  match=re.search(r"selectGongsi2?\('(\d+)'\)",row)
  if not match:continue
  cells=re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)
  if len(cells)<4 or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2}',plain(cells[3])):raise CollectionError('notice_columns_changed')
  files=[]
  for link in re.findall(r'<a\b[^>]*getFSSFileUrl.*?</a>',row,re.S):
   f=re.search(r"getFSSFileUrl\('([a-zA-Z0-9]+)'\s*,\s*'(\d+)\s*'\)",link)
   title=re.search(r'title="([^"]+)"',link)
   if f:files.append(dict(url='https://www.fss.or.kr/fss/cmmn/file/fileDown.do?'+urllib.parse.urlencode(dict(atchFileId=f[1],fileSn=f[2])),title=html.unescape(title[1]) if title else '첨부문서'))
  result.append(dict(id=key+'-'+match[1],title=plain(cells[1]),date=plain(cells[3]).replace('.','-'),url='https://dart.fss.or.kr/info/'+BOARDS[key][2]+'?seqno='+match[1],attachments=files))
 if not result:raise CollectionError('notice_rows_missing')
 if len({r['id'] for r in result})!=len(result):raise CollectionError('duplicate_notice_ids')
 return result
def merge_filings(old,observed,seen_at):
 result={r['receipt_no']:copy.deepcopy(r) for r in old};changes=[]
 for r in observed:
  prior=result.get(r['receipt_no'])
  if prior is None or any(prior.get(k)!=r.get(k) for k in ('title','filer','remarks')):
   changes.append(dict(id='filing-'+r['receipt_no']+'-'+digest(r)[:12],kind='filing' if prior is None else 'filing_metadata',title=r['title'],company_id=r['company_id'],url=r['url'],receipt_no=r['receipt_no'],date=r['received_date'],firstSeenAt=seen_at,status='awaiting_review',review='본문·첨부·회사별 적용 미검토',before=prior or {},after=r))
  result[r['receipt_no']]=r
 return sorted(result.values(),key=lambda r:r['receipt_no'],reverse=True),changes
def state_for_source(prior,source_id,title,now,ok,detail):
 result=copy.deepcopy(prior or {});result.update(id=source_id,title=title,lastAttemptAt=now,status='ok' if ok else 'failed')
 if ok:result.update(lastSuccessAt=now,detail=detail,error=None)
 else:result['error']=str(detail)
 return result
def write_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(path)
def run(root=ROOT,request=fetch,now=None):
 now=now or datetime.now(KST);stamp=now.isoformat(timespec='seconds');end=now.date().isoformat();snapshot=json.loads((root/'src/snapshot.json').read_text(encoding='utf-8'))
 path=root/'monitoring/state.json';prior=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
 baseline=prior.get('filings',snapshot['filings']);start=prior.get('collectionStart','2026-01-01')
 sources={s['id']:s for s in prior.get('sources',[])};filings=copy.deepcopy(baseline);queue={q['id']:q for q in prior.get('queue',[])};notices=copy.deepcopy(prior.get('notices',{}));documents=copy.deepcopy(prior.get('documents',{}));added=[]
 def source(sid,title,fn):
  try:detail=fn();sources[sid]=state_for_source(sources.get(sid),sid,title,stamp,True,detail)
  except Exception as e:sources[sid]=state_for_source(sources.get(sid),sid,title,stamp,False,str(e) if isinstance(e,CollectionError) else 'source_processing_failed')
 for company,(name,code) in COMPANIES.items():
  def task(company=company):
   nonlocal filings
   rows,meta=collect_filings(company,start,end,request);filings,changes=merge_filings(filings,rows,stamp);added.extend(changes);return meta
  source('filings-'+company,name+' 공시 목록',task)
 known_notice_urls={r['notice_url'] for r in snapshot['rules']}|{'https://dart.fss.or.kr/info/selectGuide.do?seqno=444'}
 for key,(title,url,detail_route) in BOARDS.items():
  def task(key=key,url=url):
   raw=request(url);rows=parse_board(decode(raw),key);old_ids={v['id'] for v in notices.values() if v['id'].startswith(key+'-')}
   if old_ids and not old_ids.intersection(r['id'] for r in rows):raise CollectionError('notice_page_overlap_lost_manual_backfill_required')
   for r in rows:
    old=notices.get(r['id']);fingerprint=digest(r)
    if old is None and (r['date']>=snapshot['asOf'] or r['date'][:4]==end[:4] and r['url'] not in known_notice_urls) or old is not None and old['fingerprint']!=fingerprint:
     added.append(dict(id='notice-'+r['id']+'-'+fingerprint[:12],kind='notice_backlog' if not prior and r['date']<snapshot['asOf'] else 'notice',title=r['title'],company_id='common',url=r['url'],date=r['date'],firstSeenAt=stamp,status='awaiting_review',review='게시물·첨부 목록 탐지 / 원문 해석·시행·회사 적용 미검토',attachments=r['attachments'],before=old.get('item',{}) if old else {},after=r))
    notices[r['id']]={'id':r['id'],'fingerprint':fingerprint,'item':r}
   return dict(rows=len(rows),scope='목록 첫 페이지 · 제목/게시일/첨부 목록 비교 · 조회수 제외',response_sha256=digest(raw),oldest_date=min(r['date'] for r in rows))
  source('board-'+key,title,task)
 watched=json.loads((root/'monitoring/watch-documents.json').read_text(encoding='utf-8'))
 for doc in watched:
  def task(doc=doc):
   raw=request(doc['url']);sha=digest(raw)
   if doc['format']=='pdf' and not raw.startswith(b'%PDF-'):raise CollectionError('expected_pdf_received_other_content')
   if doc['format']=='hwp' and not raw.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):raise CollectionError('expected_hwp_received_other_content')
   before=documents.get(doc['id'],{}).get('sha256',doc['reviewed_sha256'])
   if sha!=before:
    archive=root/'monitoring/evidence'/f"{sha}.{doc['format']}";archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(raw)
    added.append(dict(id='document-'+doc['id']+'-'+sha[:12],kind='document_change',title=doc['title'],company_id='common',url=doc['url'],date=end,firstSeenAt=stamp,status='awaiting_review',review='첨부 원본 변경 / 예외·부칙·본문·회사별 재검토 필요',before={'sha256':before},after={'sha256':sha},reviewed_sha256=doc['reviewed_sha256']))
   documents[doc['id']]=dict(sha256=sha,checkedAt=stamp,reviewed_sha256=doc['reviewed_sha256'],bytes=len(raw),url=doc['url'],changedFromReviewed=sha!=doc['reviewed_sha256'])
   return dict(sha256=sha,bytes=len(raw),matches_reviewed=sha==doc['reviewed_sha256'],scope='선정 첨부 원파일 해시 비교 · 새 내용 자동 해석 없음')
  source('document-'+doc['id'],doc['title'],task)
 for item in added:
  if item['id'] not in queue:queue[item['id']]=item
 all_sources=list(sources.values());success=sum(s['status']=='ok' for s in all_sources);status='complete' if success==len(all_sources) else 'partial' if success else 'failed'
 run_id=now.strftime('%Y%m%dT%H%M%S%z')+'-'+os.environ.get('GITHUB_RUN_ID','local')
 record=dict(id=run_id,at=stamp,status=status,ok=success,total=len(all_sources),newCandidates=sum(i['id'] not in {q['id'] for q in prior.get('queue',[])} for i in added),workflowRunUrl='https://github.com/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID'] if os.environ.get('GITHUB_REPOSITORY') and os.environ.get('GITHUB_RUN_ID') else None)
 result=dict(schemaVersion=1,schedule=dict(engine='GitHub Actions / Python',timezone='Asia/Seoul',weekdays='월~금',time='08:00',execution='cloud',aiEngine='not_connected'),lastAttemptAt=stamp,lastCompleteAt=stamp if status=='complete' else prior.get('lastCompleteAt'),lastRunStatus=status,collectionStart=start,reviewBaseline=dict(asOf=snapshot['asOf'],ruleVersion=snapshot['ruleVersion']),sources=all_sources,filings=filings,notices=notices,documents=documents,queue=sorted(queue.values(),key=lambda q:q['firstSeenAt'],reverse=True),runs=([record]+prior.get('runs',[]))[:30],limits=['수집 완료는 선정된 경로의 성공이며 전체 법규·공시 본문 전수 검토 완료가 아닙니다.','금융위 신규 게시판·KRX 법규·상장협 상세·법령센터·OpenDART 키 기반 수집은 미연결입니다.','새 공시 본문·규정 첨부 해석 및 기존 판단의 자동 수정·메일 발송은 하지 않습니다.'])
 write_json(path,result);write_json(root/'public/data/operations.json',result)
 print(json.dumps(record,ensure_ascii=False));return result
if __name__=='__main__':run()
