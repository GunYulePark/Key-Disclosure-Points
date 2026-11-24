"""Research helpers for dated filings and table facts; not approved legal rules."""
from __future__ import annotations

import re
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from collector import decode, plain
from ai_analyzer import nodes
from case_pack import validate_pack, verify_cache, require, pack_fingerprint, public_fields
from case_pack import compact


def latest_periodic(filings, start='2023.09', end='2026.09'):
    """Choose the latest receipt within each COMPANY + reporting period.

    Publication date must not replace the period in the report title. Keep every
    receipt in the version list; this function does not infer withdrawals.
    """
    groups = {}
    for row in filings:
        m = re.search(r'(?:사업|반기|분기)보고서\s*\((\d{4}\.\d{2})\)', row['title'])
        if not m or not start <= m[1] <= end:
            continue
        key = row['company_id'], m[1]
        groups.setdefault(key, []).append(row)
    result = []
    for (company, period), versions in sorted(groups.items()):
        receipts = [r['receipt_no'] for r in versions]
        if len(set(receipts)) != len(receipts):
            raise ValueError('duplicate_receipt')
        ordered = sorted(versions, key=lambda r: r['receipt_no'], reverse=True)
        result.append({'company_id': company, 'period': period, 'selected': ordered[0],
                       'versions': [r['receipt_no'] for r in ordered]})
    return result


def selected_node(main_raw, receipt, title_pattern):
    matches = [n for n in nodes(decode(main_raw)) if re.search(title_pattern, n['text'])]
    # Require an actual leaf section; duplicate titles/changed structure need review.
    if len(matches) != 1:
        raise ValueError('ambiguous_or_missing_section')
    node = matches[0]
    if node['rcpNo'] != receipt:
        raise ValueError('section_receipt_mismatch')
    return node


def asset_rows(raw):
    """Extract displayed assets from flat DART summary tables, with cell locators.

    Column periods and accounting basis require separate source evidence. This
    function deliberately does not treat the first number as year-end assets.
    """
    text = decode(raw)
    result = []
    for ti, table in enumerate(re.findall(r'<table\b[^>]*>(.*?)</table>', text, re.I | re.S)):
        if re.search(r'<table\b', table, re.I):
            raise ValueError('nested_financial_table')
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', table, re.I | re.S)
        for ri, row in enumerate(rows):
            cells = [plain(c) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.I | re.S)]
            if not cells or re.sub(r'\s+', '', cells[0]) != '자산총계':
                continue
            values = []
            for ci, cell in enumerate(cells[1:], 1):
                if not re.fullmatch(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?', cell):
                    raise ValueError('invalid_financial_number')
                values.append({'cell_index': ci, 'display': cell,
                               'decimal': str(Decimal(cell.replace(',', '')))})
            if not values:
                raise ValueError('missing_asset_values')
            result.append({'table_index': ti, 'row_index': ri, 'label': '자산총계',
                           'values': values})
    if not result:
        raise ValueError('assets_not_found')
    return result


def reported_threshold(display, unit, threshold_won='2000000000000'):
    """Arithmetic only. Unknown units fail; presentation rounding remains flagged."""
    multipliers = {'원': '1', '천원': '1000', '백만원': '1000000', '억원': '100000000'}
    if unit not in multipliers or not re.fullmatch(r'\d+(?:\.\d+)?', display):
        raise ValueError('invalid_amount_or_unit')
    try:
        amount = Decimal(display) * Decimal(multipliers[unit])
        threshold = Decimal(threshold_won)
    except InvalidOperation as e:
        raise ValueError('invalid_threshold') from e
    if not threshold.is_finite() or threshold <= 0:
        raise ValueError('invalid_threshold')
    relation = 'below' if amount < threshold else 'equal' if amount == threshold else 'above'
    return {'display_scaled_won': str(amount), 'relation_on_displayed_value': relation,
            'unit': unit, 'legal_applicability': 'not_determined',
            'presentation_precision_requires_review': unit != '원'}


def code_mentions(raw):
    """Literal mentions, NOT unique pipelines/clinical events or semantic aliases."""
    text = plain(decode(raw))
    return sorted(set(re.findall(r'(?<![A-Za-z0-9])(?:CKD-?\d{3,4}|KB-?\d{3})(?![A-Za-z0-9])', text)))


def mention_changes(before, after):
    return {'new_mentions': sorted(set(after) - set(before)),
            'not_observed_in_next_selected_section': sorted(set(before) - set(after)),
            'clinical_discontinuation_confirmed': False}


def validate_fact_links(facts, pack):
    public_fields(facts)
    validate_pack(pack)
    require(facts['human_approved'] is False and facts['active_rule'] is False,
            'unapproved_research_only')
    sources = {s['id']: s for s in pack['sources']}
    for fact in facts['asset_facts']:
        for key in ('annual', 'q3_comparative'):
            locator = fact[key]
            require(locator['source_id'] in sources, 'dangling_financial_source')
            require(all(type(locator[k]) is int and locator[k] >= 0
                        for k in ('table_index', 'row_index', 'cell_index')), 'invalid_cell_locator')
        require(fact['comparison'] == reported_threshold(fact['display_decimal'], fact['unit']),
                'financial_comparison_mismatch')
    keys = set()
    for row in facts['rd_timeline']:
        key = row['company_id'], row['period']
        require(key not in keys, 'duplicate_company_period')
        keys.add(key)
        require(row['source_id'] in sources, 'dangling_history_source')
        require(row['receipt_no'] == max(row['versions']), 'not_latest_observed_receipt')
        query = parse_qs(urlsplit(sources[row['source_id']]['url']).query)
        require(query.get('rcpNo') == [row['receipt_no']], 'history_receipt_mismatch')
    require(len(keys) == facts['selected_sections_captured'], 'history_count_mismatch')
    for company in facts['coverage']:
        require(sum(co == company for co, _ in keys) == facts['selected_periods_per_company'],
                'company_period_coverage_mismatch')
    timeline = {(r['company_id'], r['period']): r for r in facts['rd_timeline']}
    for change in facts['literal_mention_changes']:
        before = timeline[change['company_id'], change['from_period']]
        after = timeline[change['company_id'], change['to_period']]
        require(change['source_ids'] == [before['source_id'], after['source_id']], 'change_source_mismatch')
        expected = mention_changes(before['mentions'], after['mentions'])
        require(all(change[k] == value for k, value in expected.items()), 'mention_change_mismatch')
    for observation in facts['review_observations']:
        require(set(observation['source_ids']) <= sources.keys(), 'dangling_observation_source')
        require(observation['mandatory_legal_correction_confirmed'] is False, 'not_approved_correction')
    return dict(asset_facts=len(facts['asset_facts']), history_sections=len(keys),
                observations=len(facts['review_observations']), legal_accuracy_measured=False)


def verify_fact_cache(facts, pack, cache):
    result = validate_fact_links(facts, pack)
    verified = verify_cache(pack, cache)
    sources = {s['id']: s for s in pack['sources']}
    def raw(sid):
        return (Path(cache) / sources[sid]['cache_key']).read_bytes()
    parsed = {}
    for fact in facts['asset_facts']:
        for key in ('annual', 'q3_comparative'):
            locator = fact[key]; sid = locator['source_id']
            require('(단위:' + fact['unit'] + ')' in compact(plain(decode(raw(sid)))),
                    'financial_unit_not_observed')
            if sid not in parsed:
                parsed[sid] = asset_rows(raw(sid))
            matches = [r for r in parsed[sid] if (r['table_index'], r['row_index']) ==
                       (locator['table_index'], locator['row_index'])]
            values = [v for r in matches for v in r['values'] if v['cell_index'] == locator['cell_index']]
            require(len(values) == 1 and values[0]['decimal'] == fact['display_decimal'],
                    'financial_cell_mismatch')
    for row in facts['rd_timeline']:
        require(code_mentions(raw(row['source_id'])) == row['mentions'], 'mention_extraction_mismatch')
    return {**result, 'originals_verified': verified['originals_verified'],
            'financial_cells_verified': 2 * len(facts['asset_facts'])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--facts', type=Path, default=Path('research/case-followup-facts.json'))
    p.add_argument('--pack', type=Path, default=Path('research/priority-case-pack-v2.json'))
    p.add_argument('--cache', type=Path)
    args = p.parse_args()
    facts = json.loads(args.facts.read_text(encoding='utf-8-sig'))
    raw_pack = args.pack.read_bytes()
    pack = json.loads(raw_pack.decode('utf-8-sig'))
    require(pack_fingerprint(pack) == facts['source_pack_canonical_sha256'], 'source_pack_changed')
    result = verify_fact_cache(facts, pack, args.cache) if args.cache else validate_fact_links(facts, pack)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
