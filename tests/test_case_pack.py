import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from case_pack import compact, locate_anchor, validate_pack, verify_cache, verify_source, pack_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    raw = b'<html><p>Verified source version</p></html>'
    sha = hashlib.sha256(raw).hexdigest()
    source = dict(id='s1', url='https://dart.fss.or.kr/example', format='html',
                  version_label='synthetic fixture', verified_on='2026-11-24',
                  sha256=sha, bytes=len(raw), cache_key=sha+'.html',
                  anchors=[dict(id='a1', kind='text', text='Verified source version', start=0)])
    case = dict(id='C01', state='draft', human_approved=False, active_rule=False,
                source_ids=['s1'], followup=['human review'],
                questions=[dict(id='q1', text='Synthetic question', source_ids=['s1'])])
    return dict(schema_version=1, classification='public_research_inputs',
                as_of='2026-11-24', sources=[source], cases=[case]), raw


class CasePackTests(unittest.TestCase):
    def test_locator_reports_versioned_offsets_only_for_exact_original(self):
        pack, raw = fixture()
        with tempfile.TemporaryDirectory() as folder:
            source = pack['sources'][0]
            path = Path(folder) / source['cache_key']
            path.write_bytes(raw)
            location = locate_anchor(pack, folder, 'a1')
            self.assertEqual(location['sha256'], source['sha256'])
            self.assertEqual((location['normalized_start'], location['normalized_end']), (0, 21))
            self.assertIsNone(location['page_index'])
            path.write_bytes(raw + b'changed')
            with self.assertRaisesRegex(ValueError, 'original_hash_or_size_mismatch'):
                locate_anchor(pack, folder, 'a1')
    def test_metadata_fingerprint_survives_windows_newlines_but_detects_changed_content(self):
        pack, _ = fixture()
        lf = json.dumps(pack, ensure_ascii=False, indent=2)
        crlf = lf.replace('\n', '\r\n')
        self.assertNotEqual(hashlib.sha256(lf.encode()).hexdigest(), hashlib.sha256(crlf.encode()).hexdigest())
        self.assertEqual(pack_fingerprint(json.loads(lf)), pack_fingerprint(json.loads(crlf)))
        reordered = dict(reversed(list(pack.items())))
        self.assertEqual(pack_fingerprint(pack), pack_fingerprint(reordered))
        changed = copy.deepcopy(pack)
        changed['cases'][0]['questions'][0]['text'] = 'Changed question'
        self.assertNotEqual(pack_fingerprint(pack), pack_fingerprint(changed))

    def test_real_metadata_pack_is_draft_and_has_four_cases(self):
        pack = json.loads((ROOT/'research/priority-case-pack.json').read_text(encoding='utf-8'))
        result = validate_pack(pack)
        self.assertEqual((result['cases'], result['questions']), (4, 16))
        self.assertEqual((result['human_approved'], result['active_rules']), (0, 0))

    def test_duplicate_or_dangling_references_are_rejected(self):
        pack, _ = fixture()
        pack['sources'].append(copy.deepcopy(pack['sources'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate_source'):
            validate_pack(pack)
        pack, _ = fixture()
        pack['cases'][0]['questions'][0]['source_ids'] = ['unknown']
        with self.assertRaisesRegex(ValueError, 'dangling_question'):
            validate_pack(pack)

    def test_research_inputs_cannot_be_marked_approved_or_active(self):
        for field in ('human_approved', 'active_rule'):
            pack, _ = fixture()
            pack['cases'][0][field] = True
            with self.assertRaisesRegex(ValueError, 'cannot_activate'):
                validate_pack(pack)

    def test_private_answer_or_key_field_is_rejected_at_any_depth(self):
        pack, _ = fixture()
        pack['cases'][0]['questions'][0]['nested'] = {'expected_answer': 'private'}
        with self.assertRaisesRegex(ValueError, 'private_field'):
            validate_pack(pack)

    def test_future_date_and_cache_path_escape_are_rejected(self):
        pack, _ = fixture()
        pack['sources'][0]['verified_on'] = '2026-11-25'
        with self.assertRaisesRegex(ValueError, 'future_verification'):
            validate_pack(pack)
        pack, _ = fixture()
        pack['sources'][0]['cache_key'] = '../outside.html'
        with self.assertRaisesRegex(ValueError, 'invalid_cache_key'):
            validate_pack(pack)

    def test_changed_original_and_same_hash_wrong_anchor_fail(self):
        pack, raw = fixture()
        source = pack['sources'][0]
        with self.assertRaisesRegex(ValueError, 'hash_or_size'):
            verify_source(source, raw+b'changed')
        source['anchors'][0]['start'] = 1
        with self.assertRaisesRegex(ValueError, 'anchor_mismatch'):
            verify_source(source, raw)

    def test_error_page_is_not_verified_by_successful_download(self):
        pack, _ = fixture()
        raw = b'<html><p>Service unavailable</p><script>Verified source version</script></html>'
        source = pack['sources'][0]
        source.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError, 'anchor_mismatch'):
            verify_source(source, raw)

    def test_pdf_locator_cannot_reuse_text_from_another_page(self):
        import pymupdf
        pack, _ = fixture()
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50, 50), 'First page')
            doc.new_page().insert_text((50, 50), 'Second page')
            raw = doc.tobytes()
        source = pack['sources'][0]
        source.update(format='pdf', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        source['anchors'] = [dict(id='a1', kind='text', text='Second page', start=0, pdf_page=1)]
        with self.assertRaisesRegex(ValueError, 'anchor_mismatch'):
            verify_source(source, raw)
        source['anchors'][0]['pdf_page'] = 2
        verify_source(source, raw)

    def test_cache_revalidation_reports_integrity_separately_from_legal_accuracy(self):
        pack, raw = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, pack['sources'][0]['cache_key']).write_bytes(raw)
            result = verify_cache(pack, tmp)
        self.assertEqual(result['originals_verified'], 1)
        self.assertFalse(result['legal_accuracy_measured'])


if __name__ == '__main__':
    unittest.main()
