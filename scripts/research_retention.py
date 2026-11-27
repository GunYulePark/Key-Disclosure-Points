"""Plan research storage from verified article text and filing citations, offline."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from case_pack import compact, validate_pack, verified_source_pages

LEGISLATION_HOSTS = {'law.go.kr', 'www.law.go.kr', 'rule.krx.co.kr'}
GUIDANCE_HOSTS = {'www.fss.or.kr', 'www.fsc.go.kr', 'www.moj.go.kr', 'www.klca.or.kr'}
RULE_TYPES = {'legislation', 'regulation', 'filing_standard', 'guidance', 'standard_charter'}
KNOWN_GUIDANCE = {'form-1113', 'q3-lecture', 'form-notice-1113', 'bio-notice-0828', 'bio-0828'}


def retention_mode(source, document_type=None):
    url = urlsplit(source['url'])
    document_type = document_type or source.get('document_type')
    if url.hostname == 'dart.fss.or.kr' and url.path.startswith('/dsab001/'):
        return 'link'
    if url.hostname in LEGISLATION_HOSTS:
        return 'rule_text'
    official_guidance = url.hostname in GUIDANCE_HOSTS or (
        url.hostname == 'dart.fss.or.kr' and url.path.startswith('/info/'))
    if official_guidance and (document_type in RULE_TYPES or source['id'] in KNOWN_GUIDANCE):
        return 'rule_text'
    return 'excerpt'


def allow_research_original(source, permission):
    """Allow file staging only on the full-text track or with an explicit exception."""
    if retention_mode(source, permission.get('document_type')) == 'rule_text':
        return True
    reason = permission.get('full_original_reason')
    return (permission.get('full_original_exception') is True and
            isinstance(reason, str) and bool(reason.strip()))


def build_plan(pack, cache=None):
    validate_pack(pack)
    records, counts, sizes = [], Counter(), Counter()
    root = Path(cache).resolve() if cache is not None else None
    for source in pack['sources']:
        mode = retention_mode(source)
        counts[mode] += 1
        sizes[mode + '_source_bytes'] += source['bytes']
        record = {key: source[key] for key in ('id', 'url', 'version_label', 'sha256', 'format')}
        record['title'] = source.get('title') or source['id']
        record.update(mode=mode, original_bytes=source['bytes'], transfer_status='review_required')
        pages = None
        if root is not None:
            original = (root / source['cache_key']).resolve()
            if original.parent != root:
                raise ValueError('research_cache_path_escape')
            pages, _ = verified_source_pages(source, original.read_bytes())
            counts['verified_originals'] += 1
        if mode != 'link':
            evidence = []
            for anchor in source['anchors']:
                if anchor['kind'] == 'text':
                    text = anchor['text']
                    entry = dict(id=anchor['id'], text=text,
                                 normalized_start=anchor['start'],
                                 normalized_end=anchor['start'] + len(compact(text)),
                                 pdf_page=anchor.get('pdf_page'))
                    if mode == 'excerpt':
                        sizes['case_excerpt_text_bytes'] += len(text.encode('utf-8'))
                else:
                    entry = dict(id=anchor['id'], location_note=anchor['location'])
                evidence.append(entry)
            record['evidence'] = evidence
        if mode == 'rule_text' and pages is not None:
            text_bytes = '\n'.join(pages).encode('utf-8')
            sizes['rule_extracted_text_bytes'] += len(text_bytes)
            record['text_pages'] = [{'pdf_page': i if source['format'] == 'pdf' else None, 'text': page}
                                    for i, page in enumerate(pages, 1)]
            record['extracted_text_sha256'] = hashlib.sha256(text_bytes).hexdigest()
        if mode != 'rule_text':
            sizes['case_and_link_plan_json_bytes'] += len(json.dumps(
                record, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        records.append(record)
    return {'summary': {**counts, **sizes, 'cloud_writes': 0}, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=Path('research/priority-case-pack-v2.json'))
    parser.add_argument('--cache', type=Path, help='Check citation offsets and measure extracted text')
    parser.add_argument('--out', type=Path, help='Optional new JSON file under ignored .local/')
    args = parser.parse_args()
    pack = json.loads(args.pack.read_text(encoding='utf-8-sig'))
    plan = build_plan(pack, args.cache)
    if args.out:
        path = args.out.resolve()
        if not path.is_relative_to(Path('.local').resolve()):
            parser.error('--out must be under .local/')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2)
    print(json.dumps(plan['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
