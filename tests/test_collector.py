import copy, json, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collector as c
FIX=Path(__file__).parent/'fixtures'
class CollectorTests(unittest.TestCase):
 def setUp(self):self.text=(FIX/'ckd.html').read_text(encoding='utf-8')
 def test_company_identity_and_missing_count_cannot_succeed(self):
  with self.assertRaises(c.CollectionError):c.parse_filings(self.text,'kb',c.COMPANIES['kb'][1],'2026-01-01','2026-10-16')
  with self.assertRaises(c.CollectionError):c.parse_filings('<html>Access denied</html>','ckd',c.COMPANIES['ckd'][1],'2026-01-01','2026-10-16')
 def test_explicit_empty_result_and_out_of_range(self):
  self.assertEqual(c.parse_filings('총 0건','ckd',c.COMPANIES['ckd'][1],'2026-01-01','2026-10-16'),([],0))
  with self.assertRaises(c.CollectionError):c.parse_filings(self.text,'ckd',c.COMPANIES['ckd'][1],'2026-01-01','2026-01-02')
 def test_pagination_repeated_rows_and_changed_totals_stop(self):
  calls=[]
  def request(url):calls.append(url);return self.text.replace('총 1건','총 2건').encode()
  with self.assertRaises(c.CollectionError):c.collect_filings('ckd','2026-01-01','2026-10-16',request)
  self.assertEqual(len(calls),2)
 def test_new_correction_is_retained_alongside_original_and_deduplicated(self):
  rows,_=c.parse_filings(self.text,'ckd',c.COMPANIES['ckd'][1],'2026-01-01','2026-10-16');original=rows[0];correction={**original,'receipt_no':'20261016000123','title':'[기재정정] 반기보고서'}
  merged,changes=c.merge_filings([original],[correction],'now');self.assertEqual(len(merged),2);self.assertEqual(len(changes),1)
  self.assertEqual(c.merge_filings(merged,[correction],'later')[1],[])
 def test_board_ignores_read_counts_and_preserves_attachment_inventory(self):
  text=(FIX/'general.html').read_text(encoding='utf-8');rows=c.parse_board(text,'general');altered=text.replace('<td>772</td>','<td>99999</td>')
  self.assertEqual(rows,c.parse_board(altered,'general'))
  item=next(r for r in rows if r['id']=='general-450');self.assertEqual(len(item['attachments']),5);self.assertIn('fileSn=4',item['attachments'][3]['url'])
 def test_unofficial_urls_and_redirect_targets_are_rejected(self):
  for url in ['http://dart.fss.or.kr','https://dart.fss.or.kr.evil.invalid/a','https://user:pass@dart.fss.or.kr/a','https://127.0.0.1/a']:
   with self.assertRaises(c.CollectionError):c.validate_url(url)
 def test_partial_failure_keeps_last_good_data_and_does_not_fake_a_fresh_complete_run(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'src').mkdir();(root/'monitoring').mkdir()
   fixtures={k:(FIX/f'{k}.html').read_bytes() for k in ['ckd','hold','kb','general','caution']}
   all_rows=[]
   for company in c.COMPANIES:all_rows+=c.parse_filings(fixtures[company].decode(),company,c.COMPANIES[company][1],'2026-01-01','2026-10-16')[0]
   snapshot={'asOf':'2026-10-16','ruleVersion':'test','filings':all_rows,'rules':[]}
   (root/'src/snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
   old_pdf=b'%PDF-old';new_pdf=b'%PDF-new'
   (root/'monitoring/watch-documents.json').write_text(json.dumps([dict(id='test-pdf',title='Test',url='https://www.fss.or.kr/file.pdf',format='pdf',reviewed_sha256=c.digest(old_pdf))]),encoding='utf-8')
   def request(url):
    if url.endswith('file.pdf'):return old_pdf
    if 'searchGuide02' in url:return fixtures['caution']
    if 'searchGuide.do' in url:return fixtures['general']
    return next(fixtures[key] for key,(_,code) in c.COMPANIES.items() if code in url)
   first=c.run(root,request,datetime(2026,10,16,8,tzinfo=c.KST));self.assertEqual(first['lastRunStatus'],'complete')
   second=c.run(root,request,datetime(2026,10,19,8,tzinfo=c.KST));self.assertEqual(len(first['queue']),len(second['queue']))
   def partial(url):
    if 'textCrpCik=00992871' in url:raise c.CollectionError('network_failure')
    if url.endswith('file.pdf'):return new_pdf
    return request(url)
   third=c.run(root,partial,datetime(2026,10,20,8,tzinfo=c.KST))
   self.assertEqual(third['lastRunStatus'],'partial');self.assertEqual(third['lastCompleteAt'],second['lastCompleteAt']);self.assertEqual(third['filings'],second['filings'])
   failed=next(s for s in third['sources'] if s['id']=='filings-ckd');self.assertEqual(failed['lastSuccessAt'],second['lastAttemptAt'])
   self.assertTrue(any(q['kind']=='document_change' for q in third['queue']));self.assertEqual((root/'monitoring/evidence'/f'{c.digest(new_pdf)}.pdf').read_bytes(),new_pdf)
   self.assertEqual(json.loads((root/'src/snapshot.json').read_text()),snapshot)
   def blocked(url):return b'<html>Access denied</html>'
   fourth=c.run(root,blocked,datetime(2026,10,21,8,tzinfo=c.KST));self.assertEqual(fourth['lastRunStatus'],'failed');self.assertEqual(fourth['filings'],third['filings']);self.assertEqual(fourth['documents'],third['documents'])
if __name__=='__main__':unittest.main()
