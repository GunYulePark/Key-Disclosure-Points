"""Offline integrity checks for public research inputs, never legal/AI scoring.

Originals stay in ignored local cache. This module has no network, LLM, database,
mail or publication capability. Document contents are data, never instructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from collector import decode, plain

HOSTS = {'dart.fss.or.kr', 'www.fss.or.kr', 'www.fsc.go.kr', 'law.go.kr',
         'www.law.go.kr', 'kind.krx.co.kr', 'www.samsung.com', 'www.ckdpharm.com'}
FORMATS = {'html', 'pdf', 'hwp', 'jpg'}
PRIVATE_FIELDS = {'expected_answer', 'gold_answer', 'holdout_answer', 'api_key',
                  'service_role_key', 'recipient_email'}


def compact(text):
    """Whitespace-only normalization; retain punctuation, numbers and units."""
    return re.sub(r'\s+', '', text)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def public_fields(value):
    if isinstance(value, dict):
        require(not PRIVATE_FIELDS.intersection(value), 'private_field_in_public_pack')
        for child in value.values():
            public_fields(child)
    elif isinstance(value, list):
        for child in value:
            public_fields(child)


def validate_pack(pack):
    public_fields(pack)
    require(pack.get('schema_version') == 1, 'unsupported_schema')
    require(pack.get('classification') == 'public_research_inputs', 'invalid_classification')
    as_of = date.fromisoformat(pack['as_of'])
    sources = {}
    anchor_ids = set()
    for s in pack['sources']:
        require(s['id'] not in sources, 'duplicate_source')
        sources[s['id']] = s
        u = urlsplit(s['url'])
        require(u.scheme == 'https' and u.hostname in HOSTS and not u.username
                and not u.password and u.port in (None, 443), 'non_official_url')
        require(s['format'] in FORMATS, 'unsupported_format')
        require(re.fullmatch(r'[0-9a-f]{64}', s['sha256']) is not None, 'invalid_hash')
        require(type(s['bytes']) is int and s['bytes'] > 0, 'empty_source')
        require(bool(s['version_label']), 'missing_version')
        require(date.fromisoformat(s['verified_on']) <= as_of, 'future_verification')
        require(s['cache_key'] == s['sha256'] + '.' + s['format'], 'invalid_cache_key')
        require(bool(s['anchors']), 'missing_anchors')
        for a in s['anchors']:
            require(a['id'] not in anchor_ids, 'duplicate_anchor')
            anchor_ids.add(a['id'])
            require(a['kind'] in ('text', 'visual'), 'invalid_anchor_kind')
            if a['kind'] == 'text':
                require(s['format'] != 'jpg' and bool(compact(a['text'])), 'invalid_text_anchor')
                require(type(a['start']) is int and a['start'] >= 0, 'invalid_text_offset')
                if s['format'] == 'pdf':
                    require(type(a.get('pdf_page')) is int and a['pdf_page'] > 0, 'missing_pdf_page')
            else:
                require(s['format'] == 'jpg' and bool(a['location']), 'invalid_visual_anchor')
                require(date.fromisoformat(a['reviewed_on']) <= as_of, 'future_visual_review')
    cases, questions = set(), set()
    for case in pack['cases']:
        require(case['id'] not in cases, 'duplicate_case')
        cases.add(case['id'])
        require(case.get('state') == 'draft' and case.get('human_approved') is False
                and case.get('active_rule') is False, 'research_pack_cannot_activate')
        refs = set(case['source_ids'])
        require(bool(refs) and refs <= sources.keys(), 'dangling_case_source')
        require(bool(case['questions']) and bool(case['followup']), 'incomplete_case')
        for q in case['questions']:
            require(q['id'] not in questions, 'duplicate_question')
            questions.add(q['id'])
            require(bool(q['text']) and bool(q['source_ids'])
                    and set(q['source_ids']) <= refs, 'dangling_question_source')
    require(bool(cases) and bool(sources), 'empty_pack')
    return {'cases': len(cases), 'questions': len(questions), 'sources': len(sources),
            'text_anchors': sum(a['kind'] == 'text' for s in sources.values() for a in s['anchors']),
            'visual_anchors': sum(a['kind'] == 'visual' for s in sources.values() for a in s['anchors']),
            'human_approved': 0, 'active_rules': 0}


def verify_source(s, raw):
    require(len(raw) == s['bytes'] and hashlib.sha256(raw).hexdigest() == s['sha256'],
            'original_hash_or_size_mismatch:' + s['id'])
    if s['format'] == 'pdf':
        import pymupdf
        require(raw.startswith(b'%PDF-'), 'invalid_pdf')
        with pymupdf.open(stream=raw, filetype='pdf') as doc:
            pages = [compact(p.get_text()) for p in doc]
    elif s['format'] == 'html':
        pages = [compact(plain(decode(raw)))]
    elif s['format'] == 'hwp':
        from ai_analyzer import hwp_text
        pages = [compact(hwp_text(raw))]
    else:
        require(raw.startswith(b'\xff\xd8\xff'), 'invalid_jpeg')
        pages = []  # Visual inspection is recorded separately; no OCR claim.
    for a in s['anchors']:
        if a['kind'] == 'visual':
            continue
        index = a.get('pdf_page', 1) - 1
        require(0 <= index < len(pages), 'pdf_page_out_of_range:' + a['id'])
        needle = compact(a['text'])
        require(pages[index][a['start']:a['start'] + len(needle)] == needle,
                'anchor_mismatch:' + a['id'])


def verify_cache(pack, root):
    result = validate_pack(pack)
    root = Path(root).resolve()
    for s in pack['sources']:
        target = (root / s['cache_key']).resolve()
        require(target.parent == root, 'cache_path_escape')
        verify_source(s, target.read_bytes())
    return {**result, 'originals_verified': len(pack['sources']), 'legal_accuracy_measured': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack', type=Path, default=Path('research/priority-case-pack.json'))
    p.add_argument('--cache', type=Path, help='Optional ignored directory of hash-named originals')
    args = p.parse_args()
    pack = json.loads(args.pack.read_text(encoding='utf-8-sig'))
    result = verify_cache(pack, args.cache) if args.cache else validate_pack(pack)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
