import tempfile
import unittest
from pathlib import Path

from test_case_pack import fixture
from research_retention import build_plan, retention_mode


class ResearchRetentionTests(unittest.TestCase):
    def test_regulator_host_alone_does_not_make_a_case_a_rule(self):
        source = {'id': 'disciplinary-example', 'url': 'https://www.fss.or.kr/example'}
        self.assertEqual(retention_mode(source), 'excerpt')
        source['document_type'] = 'filing_standard'
        self.assertEqual(retention_mode(source), 'rule_text')

    def test_case_keeps_citations_and_rule_keeps_searchable_text_from_same_fixture(self):
        pack, raw = fixture()
        source = pack['sources'][0]
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / source['cache_key']).write_bytes(raw)
            source['url'] = 'https://dart.fss.or.kr/report/viewer.do?rcpNo=20261116000001'
            case = build_plan(pack, folder)['records'][0]
            self.assertEqual(case['mode'], 'excerpt')
            self.assertEqual(case['evidence'][0]['text'], source['anchors'][0]['text'])
            self.assertNotIn('text_pages', case)
            source['url'] = 'https://dart.fss.or.kr/dsab001/search.ax'
            listing = build_plan(pack, folder)['records'][0]
            self.assertEqual(listing['mode'], 'link')
            self.assertNotIn('evidence', listing)
            source['url'] = 'https://law.go.kr/fixture'
            rule = build_plan(pack, folder)['records'][0]
            self.assertEqual(rule['mode'], 'rule_text')
            self.assertTrue(rule['text_pages'][0]['text'])
            self.assertEqual(rule['transfer_status'], 'review_required')
