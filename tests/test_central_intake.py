from pathlib import Path
import sys
from unittest import TestCase
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from central_intake import add_site, file_for, source_url, store_entry
from central_sync import SyncError


class FixtureClient:
    workspace = '11111111-1111-4111-8111-111111111111'

    def __init__(self):
        self.row = None
        self.file = None
        self.uploads = 0
        self.fail_completion = True

    def json(self, path):
        filters = parse_qs(urlsplit(path).query)
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
