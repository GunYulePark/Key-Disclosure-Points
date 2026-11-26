import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from central_ingest import stable_id
from central_sync import BUCKET, SyncError, identity
from evidence_cloud import ViewerSessions
from serve_evidence import app, build_indexes
from test_case_pack import fixture

WORKSPACE = '11111111-1111-4111-8111-111111111111'


def cloud_fixture():
    pack, raw = fixture()
    source = pack['sources'][0]
    source['title'] = 'Example law original'
    item = identity(source, WORKSPACE)
    version = item['version_id']
    anchor = source['anchors'][0]
    rows = {
        'kdp_document_versions': [{'id': version, 'document_id': item['document_id'],
                                   'sha256': source['sha256'], 'byte_length': source['bytes'],
                                   'version_label': source['version_label'], 'processing_status': 'ready'}],
        'kdp_document_files': [{'document_version_id': version, 'bucket_id': BUCKET,
                                'object_path': item['object_path'], 'sha256': source['sha256'],
                                'byte_length': source['bytes'], 'mime_type': 'text/html',
                                'verification_status': 'verified'}],
        'kdp_sources': [{'id': stable_id('source', source['url']), 'source_url': source['url'],
                         'rights_status': 'permitted', 'transfer_approved': 'true'}],
        'kdp_evidence_spans': [{'document_version_id': version, 'legacy_evidence_id': anchor['id'],
                                'kind': 'text', 'exact_text': anchor['text'], 'normalized_text_start': anchor['start'],
                                'page_index': None, 'location_note': None, 'verification_status': 'text_verified'}],
    }
    state = {'downloads': 0, 'login_attempts': 0, 'workspace_allowed': True}

    class Reader:
        key = 'fixture-publishable'
        workspace = WORKSPACE
        def __init__(self, config, env):
            assert 'SUPABASE_DEV_SECRET_KEY' not in env
            assert 'SUPABASE_DEV_ACCESS_TOKEN' not in env
            self.token = ''

        def sign_in_with_password(self, email, password):
            state['login_attempts'] += 1
            if email != 'reader@example.test' or password != 'fixture-password':
                raise SyncError('http_400')
            self.token = 'must-stay-server-side'
            return 90

        def check_workspace(self):
            if not state['workspace_allowed']:
                raise SyncError('approved_workspace_membership_required')
            assert self.token == 'must-stay-server-side'

        def json(self, path):
            self.check_workspace()
            url = urlsplit(path)
            table = url.path.rsplit('/', 1)[-1]
            filters = parse_qs(url.query)
            assert filters.pop('workspace_id') == ['eq.' + WORKSPACE]
            filters.pop('select')
            return [r for r in rows[table]
                    if all(['eq.' + str(r[key])] == expression for key, expression in filters.items())]

        def download_original(self, source):
            self.check_workspace()
            state['downloads'] += 1
            return raw

    return pack, raw, rows, state, Reader


class CloudViewerTests(unittest.TestCase):
    def setUp(self):
        self.pack, self.raw, self.rows, self.state, reader = cloud_fixture()
        self.now = 100
        sessions = ViewerSessions({}, {'SUPABASE_DEV_SECRET_KEY': 'never-pass-this'},
                                  client_factory=reader, clock=lambda: self.now)
        self.addCleanup((root := tempfile.TemporaryDirectory()).cleanup)
        self.root = Path(root.name)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), app(0, self.root, self.root, self.pack, WORKSPACE))
        port = self.server.server_port
        self.server.RequestHandlerClass = app(port, self.root, self.root, self.pack, WORKSPACE, sessions)
        self.origin = f'http://127.0.0.1:{port}'
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.close_server)
        _, _, documents = build_indexes(self.pack, WORKSPACE)
        self.version = documents[0]['version_id']
        self.anchor = '/api/evidence/' + self.version + '/' + quote(documents[0]['anchors'][0]['id'])
        self.raw_url = '/api/original/' + self.version

    def close_server(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()

    def request(self, path, *, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        try:
            response = urlopen(Request(self.origin + path, data=data, headers=headers or {}), timeout=4)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    def form(self):
        _, _, state = self.request('/api/session')
        return {'Origin': self.origin, 'X-KDP-CSRF': json.loads(state)['csrf'],
                'Content-Type': 'application/json'}

    def login(self):
        code, headers, data = self.request('/api/session', headers=self.form(), body={
            'email': 'reader@example.test', 'password': 'fixture-password'})
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(data)['signed_in'])
        cookie = headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)
        self.assertNotIn('must-stay-server-side', cookie)
        self.assertNotIn(b'must-stay-server-side', data)
        return {'Cookie': cookie.split(';')[0]}

    def test_member_opens_cloud_evidence_and_downloads_without_local_original(self):
        for path in ('/api/catalog', self.anchor, self.raw_url):
            self.assertEqual(self.request(path)[0], 401)
        self.assertEqual(self.state['downloads'], 0)
        creds = self.login()
        code, _, body = self.request('/api/catalog', headers=creds)
        self.assertEqual(code, 200)
        self.assertEqual([s['version_id'] for s in json.loads(body)['sources']], [self.version])
        code, _, body = self.request(self.anchor, headers=creds)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['status'], 'text_verified')
        code, headers, data = self.request(self.raw_url, headers=creds)
        self.assertEqual((code, data), (200, self.raw))
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(self.state['downloads'], 2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_stale_or_cross_origin_form_never_reaches_auth_and_logout_revokes_read(self):
        form = {'email': 'reader@example.test', 'password': 'fixture-password'}
        for changed in ({'Origin': 'http://untrusted.test'}, {'X-KDP-CSRF': 'bad'}):
            code, _, _ = self.request('/api/session', body=form, headers={**self.form(), **changed})
            self.assertEqual(code, 403)
        self.assertEqual(self.state['login_attempts'], 0)
        creds = self.login()
        self.assertEqual(self.request(self.raw_url, headers={**creds, 'Sec-Fetch-Site': 'same-site'})[0], 403)
        code, headers, _ = self.request('/api/session/logout', body={}, headers={**self.form(), **creds})
        self.assertEqual(code, 200)
        self.assertIn('Max-Age=0', headers['Set-Cookie'])
        self.assertEqual(self.request(self.raw_url, headers=creds)[0], 401)

    def test_expired_or_removed_membership_cannot_read(self):
        creds = self.login()
        self.now = 200
        self.assertEqual(self.request(self.raw_url, headers=creds)[0], 401)
        creds = self.login()
        self.state['workspace_allowed'] = False
        self.assertEqual(self.request(self.raw_url, headers=creds)[0], 403)
        self.assertEqual(self.state['downloads'], 0)

    def test_removed_approval_and_different_remote_anchor_fail_closed(self):
        creds = self.login()
        self.rows['kdp_sources'][0]['transfer_approved'] = 'false'
        code, _, listing = self.request('/api/catalog', headers=creds)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(listing)['sources'], [])
        self.rows['kdp_sources'][0]['transfer_approved'] = 'true'
        self.rows['kdp_evidence_spans'][0]['normalized_text_start'] = 999
        code, _, listing = self.request('/api/catalog', headers=creds)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(listing)['sources'], [])
        self.assertEqual(self.request(self.anchor, headers=creds)[0], 422)
        self.assertEqual(self.state['downloads'], 0)
        self.rows['kdp_document_files'][0]['sha256'] = 'a' * 64
        self.assertEqual(self.request(self.raw_url, headers=creds)[0], 404)
        self.assertEqual(self.state['downloads'], 0)


if __name__ == '__main__':
    unittest.main()
