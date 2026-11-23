"""Guard reviewed-period provenance and prevent reverting to stale findings."""
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
class Q3ContentTests(unittest.TestCase):
 def test_current_period_matches_latest_corrected_receipts(self):
  review=load('src/period-review.json');snapshot=load('src/snapshot.json')
  self.assertEqual(snapshot['asOf'],review['asOf']);self.assertEqual(review['period'],'2026.09')
  expected={'ckd':'20261116002243','hold':'20261116002123','kb':'20261116001891'}
  self.assertEqual({c['id']:c['receipt_no'] for c in review['companies']},expected)
  manifest=load('public/data/q3-evidence-manifest.json')
  locations={s['url'] for c in manifest for s in c['sections']}
  for finding in snapshot['findings']:
   self.assertFalse(finding['mandatory_edit_confirmed'])
   for e in finding['evidence']:self.assertIn(e['url'],locations)
 def test_cross_company_candidates_have_both_sources(self):
  candidates=[f for f in load('src/snapshot.json')['findings'] if f['candidate']]
  self.assertEqual(len(candidates),2)
  for f in candidates:self.assertEqual({e['receipt_no'] for e in f['evidence']},{'20261116002123','20261116001891'})
 def test_old_review_is_retained_separately(self):
  snapshot=load('src/snapshot.json');old=load('public/data/review-2026-10-16.json')
  self.assertEqual(old['asOf'],'2026-10-16');self.assertEqual(snapshot['historicalFindings'],old['findings'])
  self.assertFalse({f['id'] for f in snapshot['findings']}&{f['id'] for f in old['findings']})
 def test_bio_observations_use_q3_not_old_missing_id_claim(self):
  bio=load('src/rule-reviews.json')[0]
  for c in bio['companies']:
   self.assertIn('기재',c['observed']);self.assertNotIn('선택 절에서 새 이력관리 총괄표 제목과 ID 항목은 확인되지',c['observed'])
   self.assertIn(c['evidence']['receipt_no'],{'20261116002243','20261116002123','20261116001891'})
