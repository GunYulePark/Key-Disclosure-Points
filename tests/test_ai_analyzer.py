import copy, io, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ai_analyzer as ai

URL='https://www.fss.or.kr/fss/cmmn/file/fileDown.do?atchFileId=test&fileSn=1'
TEXT='Treasury shares exception changed.'
def pdf(n=1):
 w=PdfWriter()
 for _ in range(n):
  p=w.add_blank_page(width=300,height=300)
  font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
  p[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
  stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 20 250 Td ('+TEXT+') Tj ET').encode());p[NameObject('/Contents')]=w._add_object(stream)
 b=io.BytesIO();w.write(b);return b.getvalue()
def response(value,status='completed'):
 return {'status':status,'steps':[{'type':'model_output','content':[{'type':'text','text':json.dumps(value)}]}],'usage':{'total_input_tokens':100,'total_output_tokens':200}}
def citation(source):return {'source_id':source['id'],'page':int(next(iter(source['pages']))),'quote':TEXT}

class AIReviewTests(unittest.TestCase):
 def setUp(self):
  self.config={**ai.read(ai.ROOT/'monitoring/ai-config.json',{}),'minRequestIntervalSeconds':0,'maxCallsPerDay':100}
 def test_pdf_every_page_chunked_with_original_numbers(self):
  source,parts=ai.document(pdf(5),'sample',URL,chunk_pages=2)
  self.assertEqual([list(s['pages']) for s,_ in parts],[[1,2],[3,4],[5]])
  self.assertTrue(all(TEXT in t for t in source['pages'].values()))
  self.assertTrue(all(p['mime_type']=='application/pdf' for _,p in parts))
 def test_fabricated_citations_and_quotes_rejected(self):
  source,_=ai.document(pdf(),'sample',URL)
  r={'rules':[{'citations':[citation(source)]}]};ai.evidence_check(r,[source])
  for field,value in [('page',2),('source_id','invented'),('quote','Never in this document')]:
   changed=copy.deepcopy(r);changed['rules'][0]['citations'][0][field]=value
   with self.assertRaises(ai.ReviewError):ai.evidence_check(changed,[source])
 def test_auth_error_reserves_before_call_and_does_not_leak_or_retry(self):
  state={};checkpoints=[];calls=[]
  def fail(body):
   self.assertEqual(state['attempts'][-1]['status'],'started');calls.append(body)
   raise ai.ReviewError('gemini_http_401')
  client=ai.Gemini('PRIVATE_TEST_KEY',self.config,state,lambda:checkpoints.append(copy.deepcopy(state)),fail)
  with self.assertRaises(ai.ReviewError):client.call('test','untrusted document',ai.CRITIC)
  self.assertEqual(len(calls),1);self.assertGreater(state['ledger'][ai.now()[:7]]['reservedUSD'],0)
  self.assertNotIn('PRIVATE_TEST_KEY',json.dumps(state));self.assertFalse(calls[0]['store']);self.assertNotIn('tools',calls[0])
 def test_incomplete_and_non_schema_response_never_count_as_success(self):
  for reply in (response({},'incomplete'),response({'unexpected':'field'}),{'status':'completed','steps':[]}):
   state={};client=ai.Gemini('test',self.config,state,lambda:None,lambda body:reply)
   with self.assertRaises(ai.ReviewError):client.call('test','text',ai.CRITIC)
   self.assertEqual(state['attempts'][-1]['status'],'failed')
 def test_call_limit_stops_before_network(self):
  config={**self.config,'maxCallsPerRun':0};calls=[]
  client=ai.Gemini('test',config,{},lambda:None,lambda body:calls.append(body))
  with self.assertRaises(ai.Deferred):client.call('test','text',ai.CRITIC)
  self.assertEqual(calls,[])
 def test_latest_report_uses_period_before_correction_date(self):
  state={'filings':[{'company_id':'ckd','title':'[기재정정]사업보고서 (2024.12)','receipt_no':'20261016009999'},{'company_id':'ckd','title':'반기보고서 (2026.06)','receipt_no':'20260814003547'}]}
  self.assertEqual(ai.latest_regular(state,'ckd')['receipt_no'],'20260814003547')
 def test_unsupported_attachments_and_external_urls_fail_closed(self):
  with self.assertRaises(ai.ReviewError):ai.document(b'not a PDF','bad',URL)
  with self.assertRaises(Exception):ai.document(pdf(),'bad','https://attacker.example/doc.pdf')
 def prepare(self,root):
  collected={'filings':[{'company_id':c,'title':'반기보고서 (2026.06)','receipt_no':'20260814003547'} for c in ai.COMPANIES],'documents':{},'reviewBaseline':{'asOf':'2026-10-16'},'queue':[]}
  ai.save(root/'monitoring/state.json',collected);ai.save(root/'monitoring/ai-config.json',self.config)
  ai.save(root/'monitoring/watch-documents.json',[{'id':'current-body','url':URL,'title':'current'}]);ai.save(root/'src/snapshot.json',{'findings':[]})
  return {'id':'task','title':'sample','date':'2026-10-16','kind':'notice','company_id':'common','url':URL,'attachments':[{'title':'sample','url':URL}],'after':{'revision':1}}
 def test_missing_key_exports_honest_state_without_fetching(self):
  with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'GEMINI_API_KEY':''}):
   root=Path(temp);self.prepare(root);state=ai.run(root,request=lambda _:self.fail('must not fetch'))
   self.assertEqual(state['status'],'needs_key');self.assertEqual(state['results'],[])
   public=ai.read(root/'public/data/ai-analysis.json',{});self.assertNotIn('cache',public)
 def test_full_pipeline_resume_cache_and_unapproved_publication(self):
  with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'GEMINI_API_KEY':'TEST_ONLY'}):
   root=Path(temp);task=self.prepare(root);config={**self.config,'maxCallsPerRun':1};ai.save(root/'monitoring/ai-config.json',config)
   calls=[];source,_=ai.document(pdf(),'sample',URL)
   company_sources=[{**source,'id':'company-'+c,'title':c+' report','company_id':c,'format':'html-text-segments'} for c in ai.COMPANIES]
   def transport(body):
    calls.append(body);p=json.loads(body['input'][-1]['text']);fields=body['response_format']['schema']['properties']
    if 'rules' in fields:return response({'summary':'extracted','topics':['Treasury'],'rules':[{'title':'changed','before':'old','after':'new','effective_date':'unknown','conditions':'review','nature':'unknown','citations':[citation(source)]}],'limitations':[]})
    if 'findings' in fields:return response({'summary':'review','findings':[{'company_id':p['company'],'priority':'P1','title':'candidate','before':'old','after':'new','action':'verify','applicability':'candidate_required','effective_date':'unknown','correction_candidate':True,'uncertainty':'human review','citations':[citation(source),citation(next(x for x in company_sources if x['company_id']==p['company']))]}],'limitations':['selected sections only']})
    return response({'verdict':'needs_review','issues':['Verify applicability date']})
   with patch.object(ai,'task_list',return_value=[task]),patch.object(ai,'contexts',return_value=(company_sources,[])):
    first=ai.run(root,request=lambda _:pdf(),transport=transport)
    self.assertEqual(first['status'],'deferred');self.assertEqual(first['results'],[])
    runs=[first]
    for _ in range(6):runs.append(ai.run(root,request=lambda _:pdf(),transport=transport))
    self.assertEqual(runs[2]['status'],'deferred');self.assertEqual(len(runs[2]['results']),1)
    self.assertEqual(runs[-1]['status'],'complete');self.assertEqual(len(calls),7);self.assertEqual(len(runs[-1]['results']),3)
    for result in runs[-1]['results']:
     self.assertFalse(result['humanApproved']);self.assertEqual(result['critique']['verdict'],'needs_review')
    cached=ai.run(root,request=lambda _:self.fail('cached completed task fetched again'),transport=transport)
    self.assertEqual(len(cached['results']),3);self.assertEqual(len(calls),7)
    s=ai.read(root/'monitoring/state.json',{});s['documents']['current-body']={'sha256':'changed'};ai.save(root/'monitoring/state.json',s)
    changed=ai.run(root,request=lambda _:pdf(),transport=transport)
    self.assertEqual(len(changed['results']),6);self.assertEqual(len(calls),7) # actual downloaded evidence identical: reuse validated stages

 def test_429_defers_and_persists_cooldown(self):
  state={}
  def limited(body):raise ai.RateLimited('gemini_http_429')
  client=ai.Gemini('test',self.config,state,lambda:None,limited)
  with self.assertRaises(ai.Deferred):client.call('test','text',ai.CRITIC)
  self.assertIn('quotaNotBefore',state);self.assertEqual(state['attempts'][-1]['error'],'gemini_http_429')
  with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'GEMINI_API_KEY':'test'}):
   root=Path(temp);self.prepare(root);ai.save(root/'monitoring/ai-state.json',{**state,'results':[],'cache':{},'tasks':{},'schemaVersion':1})
   result=ai.run(root,request=lambda _:self.fail('cooldown must not fetch or call'))
   self.assertEqual(result['status'],'deferred');self.assertEqual(result['error'],'free_quota_cooldown')
 def test_pacing_and_payload_guard(self):
  state={'attempts':[{'at':ai.now(),'status':'completed'}]};waits=[]
  config={**self.config,'minRequestIntervalSeconds':75}
  client=ai.Gemini('test',config,state,lambda:None,lambda body:response({'verdict':'no_objection','issues':[]}),sleep=waits.append)
  client.call('test','text',ai.CRITIC);self.assertEqual(len(waits),1);self.assertGreater(waits[0],70)
  with self.assertRaises(ai.ReviewError):client.call('test','x'*config['maxInputBound'],ai.CRITIC)
 def test_snippet_budget_keeps_original_locations(self):
  source={'id':'s','title':'sample','pages':{9:TEXT*200},'format':'html-text-segments'}
  selected=ai.snippets([source],['Treasury'],4000)
  self.assertTrue(selected);self.assertEqual(list(selected[0]['pages']),[9]);self.assertLess(len(json.dumps(ai.pack(selected)).encode()),5000)
 def test_daily_limit_survives_new_client(self):
  state={};calls=[];config={**self.config,'maxCallsPerDay':1}
  def transport(body):calls.append(body);return response({'verdict':'no_objection','issues':[]})
  ai.Gemini('test',config,state,lambda:None,transport).call('first','text',ai.CRITIC)
  with self.assertRaises(ai.Deferred):ai.Gemini('test',config,state,lambda:None,transport).call('second','text',ai.CRITIC)
  self.assertEqual(len(calls),1)
 def test_identical_files_at_different_urls_keep_citation_identity(self):
  raw=pdf();one=ai.document(raw,'one',URL);two=ai.document(raw,'two',URL+'&other=2');calls=[];state={};cache={}
  def transport(body):
   calls.append(body);s=json.loads(body['input'][-1]['text'])['source'][0]
   return response({'summary':'change','topics':['Treasury'],'rules':[{'title':'rule','before':'old','after':'new','effective_date':'unknown','conditions':'review','nature':'unknown','citations':[{'source_id':s['id'],'page':1,'quote':TEXT}]}],'limitations':[]})
  client=ai.Gemini('test',self.config,state,lambda:None,transport)
  units=list(ai.extraction_units([one,two],client,cache,lambda:None))
  self.assertEqual(len(calls),2);self.assertNotEqual(units[0][0],units[1][0])
  for _,partial,result in units:ai.evidence_check(result,[partial])
 def test_required_change_needs_company_and_rule_evidence(self):
  source,_=ai.document(pdf(),'rule',URL);company={**source,'id':'company','company_id':'ckd','title':'ckd report'}
  extract={'summary':'change','topics':['Treasury'],'rules':[{'title':'Treasury','before':'old','after':'new','conditions':'check','effective_date':'unknown','nature':'unknown','citations':[citation(source)]}],'limitations':[]}
  finding={'company_id':'ckd','priority':'P1','title':'candidate','before':'old','after':'new','action':'verify','applicability':'candidate_required','effective_date':'unknown','correction_candidate':True,'uncertainty':'review','citations':[citation(source)]}
  state={'results':[],'cache':{}};client=ai.Gemini('test',self.config,state,lambda:None,lambda body:response({'summary':'review','findings':[finding],'limitations':[]}))
  with self.assertRaisesRegex(ai.ReviewError,'missing_company_or_rule_evidence'):
   ai.review_unit('sig','unit',0,extract,source,'ckd',[company],[],[],{'id':'task','title':'sample','date':'2026-10-16','kind':'notice'},{'analysisDate':'2026-10-16'},client,state,lambda:None)
  self.assertEqual(state['results'],[])

if __name__=='__main__':unittest.main()
