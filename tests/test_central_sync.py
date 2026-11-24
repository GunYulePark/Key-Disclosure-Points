import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from central_sync import Client, NoRedirect, SyncError, make_plan, safe_target, target_config
from central_contract import document_id
from test_case_pack import fixture

WS = '11111111-1111-4111-8111-111111111111'
REF = 'a' * 20


def env():
    return {'APP_ENV': 'development', 'CENTRAL_STORE_MODE': 'supabase',
            'SUPABASE_DEV_PROJECT_REF': REF, 'SUPABASE_DEV_URL': f'https://{REF}.supabase.co',
            'SUPABASE_DEV_WORKSPACE_ID': WS, 'SUPABASE_DEV_PUBLISHABLE_KEY': 'fixture-publishable',
            'SUPABASE_DEV_ACCESS_TOKEN': 'fixture-user-jwt', 'SUPABASE_DEV_SECRET_KEY': 'fixture-server-secret'}


def target():
    return {'purpose': 'kdp-development', 'project_ref': REF, 'workspace_id': WS, 'approved': True}


class SyncTests(unittest.TestCase):
    def test_offline_plan_does_not_call_network_or_approve_transfer(self):
        pack, _ = fixture()
        with patch('central_sync.build_opener', side_effect=AssertionError('network forbidden')):
            plan = make_plan(pack, WS)
        self.assertEqual(plan['cloud_writes'], 0)
        self.assertFalse(plan['transfer_approved'])
        self.assertFalse(plan['local_originals_verified'])
        self.assertEqual(plan['items'][0]['document_id'], document_id(pack['sources'][0]['url'], 's1'))

    def test_real_pack_plan_preserves_76_original_identities(self):
        pack = json.loads((Path(__file__).resolve().parents[1] / 'research/priority-case-pack-v2.json').read_text('utf8'))
        plan = make_plan(pack, WS)
        self.assertEqual((plan['sources'], plan['bytes']), (76, 27024097))
        self.assertEqual(len({i['object_path'] for i in plan['items']}), 76)
        self.assertTrue(all(i['object_path'].startswith(WS + '/originals/') for i in plan['items']))

    def test_changed_or_missing_cache_cannot_pass(self):
        pack, raw = fixture()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                make_plan(pack, WS, folder)
            path = Path(folder) / pack['sources'][0]['cache_key']
            path.write_bytes(raw)
            self.assertTrue(make_plan(pack, WS, folder)['local_originals_verified'])
            path.write_bytes(raw + b'changed')
            with self.assertRaisesRegex(ValueError, 'hash_or_size'):
                make_plan(pack, WS, folder)

    def test_wrong_target_workspace_mode_or_url_are_blocked(self):
        for key, value in [('APP_ENV', 'production'), ('CENTRAL_STORE_MODE', 'disabled'),
                           ('SUPABASE_DEV_URL', 'https://example.com'),
                           ('SUPABASE_DEV_WORKSPACE_ID', '22222222-2222-4222-8222-222222222222'),
                           ('SUPABASE_DEV_STORAGE_BUCKET', 'public')]:
            e = env(); e[key] = value
            with self.subTest(key=key), self.assertRaises(SyncError):
                target_config(target(), e)
        config = target(); config['approved'] = False
        with self.assertRaisesRegex(SyncError, 'approved_development'):
            target_config(config, env())

    def test_no_redirect_can_leak_credentials(self):
        with self.assertRaisesRegex(SyncError, 'unexpected_http_redirect'):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')

    def test_existing_public_bucket_is_not_modified(self):
        client = Client(target(), env())
        with patch.object(client, 'json', return_value={'id': 'kdp-dev-originals', 'public': True}), \
                patch.object(client, 'request') as write:
            with self.assertRaisesRegex(SyncError, 'not_private'):
                client.check_bucket(create=True)
            write.assert_not_called()

    def test_bucket_creation_requires_explicit_apply(self):
        client = Client(target(), env())
        with patch.object(client, 'json', side_effect=SyncError('http_404')), patch.object(client, 'request') as write:
            with self.assertRaisesRegex(SyncError, 'http_404'):
                client.check_bucket(create=False)
            write.assert_not_called()
        with patch.object(client, 'json', side_effect=[SyncError('http_404'), {'id': 'kdp-dev-originals', 'public': False}]), \
                patch.object(client, 'request') as write:
            self.assertTrue(client.check_bucket(create=True)['private'])
            self.assertIs(write.call_args.kwargs['body']['public'], False)

    def test_http_failure_does_not_echo_body_or_secret(self):
        client = Client(target(), env())
        client.opener.open = lambda *a, **k: (_ for _ in ()).throw(
            HTTPError(client.url, 403, 'private', {}, io.BytesIO(b'fixture-server-secret')))
        with self.assertRaisesRegex(SyncError, '^http_403$'):
            client.request('/storage/v1/bucket/kdp-dev-originals', server=True)

    def test_reader_requires_jwt_and_cache_traversal_denied(self):
        e = env(); e.pop('SUPABASE_DEV_ACCESS_TOKEN')
        client = Client(target(), e)
        with self.assertRaisesRegex(SyncError, 'authenticated_reader'):
            client.request('/rest/v1/kdp_documents')
        with self.assertRaisesRegex(SyncError, 'invalid_cache_key'):
            safe_target('.', '../outside.html')

    def test_restore_verifies_db_manifest_bytes_anchors_and_preserves_existing(self):
        pack, raw = fixture()
        client = Client(target(), env())
        item = make_plan(pack, WS)['items'][0]
        row = {'object_path': item['object_path'], 'sha256': item['sha256'],
               'byte_length': item['bytes'], 'verification_status': 'verified'}
        with tempfile.TemporaryDirectory() as folder, patch.object(client, 'json', return_value=[row]), \
                patch.object(client, 'request', return_value=raw) as fetch:
            self.assertEqual(client.restore(pack, folder)['restored'], 1)
            self.assertEqual(client.restore(pack, folder)['cached_verified'], 1)
            self.assertEqual(fetch.call_count, 1)
            path = Path(folder) / item['cache_key']
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash_or_size'):
                client.restore(pack, folder)
            self.assertEqual(path.read_bytes(), b'changed')

    def test_bad_or_unverified_remote_original_never_written(self):
        pack, raw = fixture()
        client = Client(target(), env())
        item = make_plan(pack, WS)['items'][0]
        row = {'object_path': item['object_path'], 'sha256': item['sha256'],
               'byte_length': item['bytes'], 'verification_status': 'staged'}
        with tempfile.TemporaryDirectory() as folder, patch.object(client, 'json', return_value=[row]), \
                patch.object(client, 'request', return_value=raw + b'bad'):
            with self.assertRaisesRegex(SyncError, 'verified_file_manifest'):
                client.restore(pack, folder)
            row['verification_status'] = 'verified'
            with self.assertRaisesRegex(ValueError, 'hash_or_size'):
                client.restore(pack, folder)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
