import copy
import unittest

from test_case_pack import fixture
from case_pack import pack_fingerprint
from central_ingest import approved_batch, migration_sql, records
from central_sync import SyncError, identity
from test_central_sync import WS, env, target


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.pack, _ = fixture()
        self.source = self.pack['sources'][0]
        self.source['title'] = "Test $payload$ and $ingest$ document"
        self.approval = {
            **target(), 'pack_fingerprint': pack_fingerprint(self.pack),
            'transfer_approved': True, 'approved_by': 'fixture operator',
            'sources': {'s1': {'sha256': self.source['sha256'],
                               'rights_url': 'https://example.test/rights',
                               'publisher': 'fixture publisher', 'document_type': 'legislation'}},
        }

    def test_approval_is_scoped_to_pack_target_and_exact_bytes(self):
        for key in ('transfer_approved', 'pack_fingerprint', 'project_ref', 'workspace_id'):
            with self.subTest(key=key):
                invalid = {**self.approval, key: 'wrong'}
                with self.assertRaisesRegex(SyncError, 'explicit_batch_approval_required'):
                    list(approved_batch(self.pack, invalid, target(), env()))
        invalid = copy.deepcopy(self.approval)
        invalid['sources']['s1']['sha256'] = 'b' * 64
        with self.assertRaisesRegex(SyncError, 'source_rights_or_identity_invalid'):
            list(approved_batch(self.pack, invalid, target(), env()))

    def test_original_path_is_compatible_with_restore_and_sql_quotes_are_distinct(self):
        batch = list(approved_batch(self.pack, self.approval, target(), env()))
        entries = records(batch, self.approval['approved_by'])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['object_path'], identity(self.source, WS)['object_path'])
        self.assertTrue(migration_sql(entries).startswith('DO $ingest_$'))
        self.assertIn('$payload_$[{', migration_sql(entries))
        self.assertNotIn('update public.kdp_document_files', migration_sql(entries))
