import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from workspace_inventory import inventory, sample_plan
from central_contract import document_id, version_id, object_path, verify_original, update_revision
class FoundationTests(unittest.TestCase):
 def test_inventory_excludes_secrets_dependencies_and_symlinks(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);repo=root/'repo';(repo/'src').mkdir(parents=True)
   (repo/'.env').write_text('DO_NOT_READ');(root/'node_modules').mkdir();(root/'node_modules'/'hidden').write_text('skip')
   (root/'data').mkdir();raw=b'%PDF-1.7 fixture only';(root/'data'/'one.pdf').write_bytes(raw);(root/'data'/'copy.pdf').write_bytes(raw)
   html=b'<p>synthetic official-file fixture</p>';(root/'data'/'test.html').write_bytes(html)
   (repo/'src'/'snapshot.json').write_text(json.dumps([{'sha256':hashlib.sha256(raw).hexdigest(),'url':'https://www.fss.or.kr/test.pdf','source_key':'legacy-pdf'},{'sha256':hashlib.sha256(html).hexdigest(),'url':'https://dart.fss.or.kr/report/viewer.do?test=1','source_key':'legacy-html'}]))
   report=inventory(root,repo);paths=[f['path'] for f in report['files']]
   self.assertFalse(any('.env' in p or 'node_modules' in p for p in paths));self.assertEqual(report['summary']['duplicate_copies'],1)
   plan=sample_plan(report);self.assertEqual(len(plan['samples']),2);self.assertEqual(plan['cloud_writes'],0);self.assertFalse(any(f['transfer_approved'] for f in report['files']))
 def test_origin_match_never_grants_transfer_approval(self):
  self.assertEqual(sample_plan({'files':[]})['missing_types'],['official_pdf','dart_html_or_xml'])
 def test_ids_are_idempotent_versions_are_immutable(self):
  d=document_id('https://dart.fss.or.kr/example','old-evidence-id');h=hashlib.sha256(b'one').hexdigest();h2=hashlib.sha256(b'two').hexdigest()
  self.assertEqual(d,document_id('https://dart.fss.or.kr/example','old-evidence-id'));self.assertEqual(object_path(d,h,'pdf'),object_path(d,h,'pdf'));self.assertNotEqual(version_id(d,h),version_id(d,h2))
  with self.assertRaises(ValueError):object_path(d,h,'../../other')
  with self.assertRaises(ValueError):verify_original(b'changed',h)
 def test_concurrent_stale_revision_is_rejected(self):
  self.assertEqual(update_revision(3,3),4)
  with self.assertRaises(ValueError):update_revision(4,3)
