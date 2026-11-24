import sys
import unittest
import json
import copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from case_followup import (latest_periodic, selected_node, asset_rows,
                           reported_threshold, code_mentions, mention_changes, validate_fact_links)


def row(company, receipt, title):
    return dict(company_id=company, receipt_no=receipt, title=title)


class FollowupTests(unittest.TestCase):
    def test_real_followup_preserves_all_company_periods_and_draft_status(self):
        root = Path(__file__).resolve().parents[1]
        facts = json.loads((root/'research/case-followup-facts.json').read_text(encoding='utf-8'))
        pack = json.loads((root/'research/priority-case-pack-v2.json').read_text(encoding='utf-8'))
        result = validate_fact_links(facts, pack)
        self.assertEqual((result['asset_facts'], result['history_sections']), (5, 39))
        self.assertFalse(result['legal_accuracy_measured'])

    def test_dangling_fact_and_fabricated_discontinuation_are_rejected(self):
        root = Path(__file__).resolve().parents[1]
        facts = json.loads((root/'research/case-followup-facts.json').read_text(encoding='utf-8'))
        pack = json.loads((root/'research/priority-case-pack-v2.json').read_text(encoding='utf-8'))
        altered = copy.deepcopy(facts)
        altered['asset_facts'][0]['annual']['source_id'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'dangling_financial_source'):
            validate_fact_links(altered, pack)
        altered = copy.deepcopy(facts)
        altered['literal_mention_changes'][0]['clinical_discontinuation_confirmed'] = True
        with self.assertRaisesRegex(ValueError, 'mention_change_mismatch'):
            validate_fact_links(altered, pack)

    def test_late_correction_keeps_reporting_period_and_all_versions(self):
        rows = [row('ckd','20260814003547','반기보고서 (2026.06)'),
                row('ckd','20261022000500','[기재정정]반기보고서 (2026.06)'),
                row('ckd','20261116002243','[기재정정]분기보고서 (2026.09)')]
        groups = latest_periodic(rows)
        self.assertEqual([g['period'] for g in groups], ['2026.06', '2026.09'])
        self.assertEqual(groups[0]['versions'], ['20261022000500', '20260814003547'])

    def test_company_and_window_boundaries_do_not_mix(self):
        rows = [row('ckd','20240320000001','사업보고서 (2023.12)'),
                row('hold','20240321000001','사업보고서 (2023.12)'),
                row('ckd','20261022000001','[기재정정]반기보고서 (2023.06)')]
        self.assertEqual(len(latest_periodic(rows)), 2)
        with self.assertRaisesRegex(ValueError, 'duplicate_receipt'):
            latest_periodic(rows + rows[:1])

    def test_summary_preserves_column_order_and_cell_locator(self):
        raw = '<table><tr><th>구분</th><th>2026.09</th><th>2025.12</th></tr><tr><td>자산총계</td><td>1,873,784</td><td>1,800,298</td></tr></table>'.encode()
        result = asset_rows(raw)[0]
        self.assertEqual(result['row_index'], 1)
        self.assertEqual(result['values'][1], dict(cell_index=2, display='1,800,298', decimal='1800298'))

    def test_missing_assets_and_placeholder_are_not_zero(self):
        with self.assertRaisesRegex(ValueError, 'assets_not_found'):
            asset_rows(b'<table><tr><td>Other</td><td>0</td></tr></table>')
        with self.assertRaisesRegex(ValueError, 'invalid_financial_number'):
            asset_rows('<table><tr><td>자산총계</td><td>-</td></tr></table>'.encode())
        self.assertEqual(asset_rows('<table><tr><td>자산총계</td><td>0</td></tr></table>'.encode())[0]['values'][0]['decimal'], '0')

    def test_nested_table_requires_review_instead_of_false_locator(self):
        raw = '<table><tr><td><table><tr><td>자산총계</td><td>1</td></tr></table></td></tr></table>'.encode()
        with self.assertRaisesRegex(ValueError, 'nested_financial_table'):
            asset_rows(raw)

    def test_threshold_uses_decimal_and_inclusive_boundary_without_legal_activation(self):
        self.assertEqual(reported_threshold('1999999.999999','백만원')['relation_on_displayed_value'], 'below')
        result = reported_threshold('2000000','백만원')
        self.assertEqual(result['relation_on_displayed_value'], 'equal')
        self.assertEqual(result['legal_applicability'], 'not_determined')
        self.assertTrue(result['presentation_precision_requires_review'])
        self.assertEqual(reported_threshold('2000001','백만원')['relation_on_displayed_value'], 'above')

    def test_invalid_units_and_nonfinite_thresholds_are_rejected(self):
        for args in [('1','USD','2'), ('NaN','원','2'), ('1','원','Infinity'), ('1','원','-1')]:
            with self.assertRaises(ValueError):
                reported_threshold(*args)

    def test_literal_codes_do_not_merge_aliases_or_imply_unique_pipeline(self):
        result = code_mentions(b'<p>CKD510 CKD-510 KB-001 KB001 CKD-510</p>')
        self.assertEqual(result, ['CKD-510','CKD510','KB-001','KB001'])

    def test_disappearing_mentions_are_not_clinical_discontinuation(self):
        result = mention_changes(['CKD-386'], [])
        self.assertEqual(result['not_observed_in_next_selected_section'], ['CKD-386'])
        self.assertFalse(result['clinical_discontinuation_confirmed'])

    def test_selected_section_rejects_wrong_receipt_and_duplicate_heading(self):
        block = '''var node1 = {};
node1['text'] = "6. 주요계약 및 연구개발활동";
node1['rcpNo'] = "20261116002243";
node1['dcmNo'] = "11662807";
node1['eleId'] = "17";
node1['offset'] = "10";
node1['length'] = "100";
node1['dtd'] = "dart4.xsd";'''.encode()
        with self.assertRaisesRegex(ValueError, 'receipt_mismatch'):
            selected_node(block, 'wrong', '주요계약')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            selected_node(block+block, '20261116002243', '주요계약')
        self.assertEqual(selected_node(block, '20261116002243', '주요계약')['eleId'], '17')


if __name__ == '__main__':
    unittest.main()
