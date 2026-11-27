"""Local candidate links from short excerpts, exact public URLs and reviewer notes."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

CATALOGUE = Path(__file__).resolve().parents[1] / 'src/disclosure-cases.json'
TOPICS = {
    'treasury': ('자기주식보고서', '첨부예외'),
    'treasury-disposal': ('자기주식소각', '자기주식보유처분', '교환사채'),
    'cumulative-voting': ('집중투표', '542조의7'),
    'independent-director': ('독립이사', '사외이사', '542조의8'),
    'audit-election': ('감사위원', '분리선임', '542조의12', '3%의결권'),
    'electronic-meeting': ('전자주주총회', '전자주총', '전자위임장', '전자문서대리'),
    'director-duty': ('충실의무', '공평대우', '382조의3'),
    'dividend': ('배당기준일', '배당예측가능성', '배당액확정'),
    'bio': ('파이프라인', '연구개발', '마일스톤'),
    'filing-correction': ('정정표', '기재정정', '정정공시'),
}


def compact(text):
    return re.sub(r'\s+', '', text)


def pdf_preview(raw):
    if raw is None:
        return ''
    import pymupdf
    try:
        with pymupdf.open(stream=raw, filetype='pdf') as document:
            return '\n'.join(document[i].get_text()[:3000] for i in range(min(8, len(document))))
    except (RuntimeError, ValueError):
        return ''


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(CATALOGUE.read_text(encoding='utf-8'))


def filing_number(url):
    parts = urlsplit(url)
    return parse_qs(parts.query).get('rcpNo', [''])[0] if parts.hostname == 'dart.fss.or.kr' else ''


def candidate_cases(title, points, url, body='', pdf=None):
    short_text = compact(title + ' ' + points)
    excerpt = compact((body or '')[:24000] + pdf_preview(pdf))
    receipt = filing_number(url or '')
    scores = []
    for case in catalogue():
        terms = TOPICS.get(case['id'], ())
        score = sum(4 for term in terms if term in short_text)
        score += sum(1 for term in terms if term in excerpt)
        links = list(case['ruleSources'])
        for group in (*case['checks'], *case['examples']):
            links.extend(group.get('sources', []))
        if url and any(url == source['url'] for source in links):
            score += 9
        elif receipt and any(receipt == filing_number(source['url']) for source in links):
            score += 2
        if score:
            scores.append((score, case['id']))
    scores.sort(key=lambda item: (-item[0], item[1]))
    return [case_id for _, case_id in scores[:5]]


def case_links(ids):
    names = {item['id']: item['title'] for item in catalogue()}
    return [{'id': case_id, 'title': names[case_id]} for case_id in ids if case_id in names]
