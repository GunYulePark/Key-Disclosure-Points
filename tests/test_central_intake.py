from pathlib import Path
import sys
from unittest import TestCase
from urllib.parse import parse_qs, urlsplit
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from central_intake import add_site, file_for, notes_for, source_url, store_entry
from central_sync import SyncError
from intake_context import candidate_cases


class FixtureClient:
    workspace = '11111111-1111-4111-8111-111111111111'

    def __init__(self):
        self.row = None
        self.file = None
        self.notes = {}
        self.uploads = 0
        self.fail_completion = True

    def json(self, path):
        filters = parse_qs(urlsplit(path).query)
        if path.startswith('/rest/v1/kdp_intake_notes'):
            return [dict(row) for row in self.notes.values() if filters['intake_id'] == ['eq.' + row['intake_id']]]
        if self.row and filters['id'] == ['eq.' + self.row['id']]:
            return [dict(self.row)]
        return []

    def request(self, path, method='GET', body=None, content_type=None):
        if path.startswith('/rest/v1/kdp_intake_entries'):
            if method == 'POST':
                if self.row:
                    raise SyncError('http_409')
                object_path = self.workspace + '/intake/' + body['id'] + '.pdf'
                self.row = dict(body, stored_at=None, object_path=object_path)
            elif method == 'PATCH':
                if self.fail_completion:
                    self.fail_completion = False
                    raise SyncError('network_failure')
                self.row['stored_at'] = '2026-11-27'
        elif path == '/rest/v1/kdp_intake_notes':
            if body['id'] in self.notes:
                raise SyncError('http_409')
            self.notes[body['id']] = body
        elif path.startswith('/storage/v1/'):
            if method == 'POST':
                assert content_type == 'application/pdf'
                self.file = body
                self.uploads += 1
            elif self.file is None:
                raise SyncError('http_404')
            return self.file


class CentralIntakeTests(TestCase):
    metadata = dict(title='시험 원본', company_id='all', source_url='https://www.example.org/',
                    rights_basis='시험 자료')

    def test_pdf_partial_failure_reopens_existing_object_and_checks_hash(self):
        client = FixtureClient()
        pdf = b'%PDF-test'
        with self.assertRaisesRegex(SyncError, 'network_failure'):
            store_entry(client, self.metadata, pdf=pdf)
        entry_id = store_entry(client, self.metadata, pdf=pdf)
        self.assertEqual(entry_id, store_entry(client, self.metadata, pdf=pdf))
        self.assertEqual(client.uploads, 1)
        self.assertEqual(file_for(client, entry_id), pdf)
        client.file = b'%PDF-fail'
        with self.assertRaisesRegex(ValueError, 'intake_integrity_failed'):
            file_for(client, entry_id)

    def test_text_retains_original_and_url_normalizes_without_fetching(self):
        client = FixtureClient()
        text = '  원문 그대로\n'
        store_entry(client, dict(self.metadata, text=text))
        self.assertEqual(client.row['body_text'], text)
        self.assertEqual(client.row['byte_length'], len(text.encode()))
        self.assertEqual(source_url('https://Example.org:443'), 'https://example.org/')
        for invalid in ('http://example.com', 'https://user@example.org', 'https://example.org\\abc'):
            with self.assertRaises(ValueError):
                source_url(invalid)
        self.assertEqual(add_site(client, dict(title='공시', category='filing', url='https://example.org')),
                         {'existing': False})

    def test_pdf_cannot_enter_without_file_and_storage_basis(self):
        client = FixtureClient()
        with self.assertRaises(ValueError):
            store_entry(client, dict(self.metadata, rights_basis=''), pdf=b'%PDF-example')
        with self.assertRaisesRegex(ValueError, 'invalid_intake_pdf'):
            store_entry(client, self.metadata, pdf=b'<html>')
        self.assertIsNone(client.row)

    def test_link_saves_notes_without_downloading_or_duplicating_original(self):
        client = FixtureClient()
        payload = dict(self.metadata, review_points='배당 기준일 변경 확인')
        entry_id = store_entry(client, payload, link_only=True)
        self.assertEqual(entry_id, store_entry(client, payload, link_only=True))
        store_entry(client, dict(payload, review_points='감사위원 분리선임 확인'), link_only=True)
        self.assertEqual(client.row['origin_format'], 'link')
        self.assertEqual(client.row['body_text'], self.metadata['source_url'])
        self.assertIsNone(client.file)
        self.assertEqual(len(client.notes), 2)
        self.assertEqual([note['related_cases'][0]['id'] for note in notes_for(client, entry_id)],
                         ['dividend', 'audit-election'])

    def test_official_filing_receipt_and_document_text_are_matched(self):
        url = 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260601800818'
        self.assertEqual(candidate_cases('검토', '', url)[0], 'dividend')
        self.assertEqual(candidate_cases('검토', '', None, '연구 개발 파이프라인'), ['bio'])

    def test_selectable_text_from_pdf_matches_independent_director(self):
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 40), '독립이사', fontname='korea')
            self.assertEqual(candidate_cases('검토', '', None, pdf=pdf.tobytes()), ['independent-director'])
