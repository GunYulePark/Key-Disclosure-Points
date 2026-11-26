import hashlib
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from case_pack import compact
from collector import plain
from evidence_view import evidence_view
from serve_evidence import app, build_indexes
from test_case_pack import fixture


def all_nodes(nodes):
    for node in nodes:
        yield node
        yield from all_nodes(node.get('children', []))


class EvidenceViewTests(unittest.TestCase):
    def test_marks_selected_duplicate_cell_and_preserves_table_without_active_content(self):
        text = ('<p>같은 금액</p><table onclick="alert(1)"><tr><th colspan="2">기준</th></tr>'
                '<tr><td rowspan="2">대상</td><td><a href="javascript:alert(1)">같은 <b>금액</b></a></td></tr>'
                '<tr><td>음수 (1,200)</td></tr></table><img src="https://example.org/pixel">'
                '<script>alert(2)</script><style>p{display:none}</style>')
        normalized = compact(plain(text))
        needle = '같은금액'
        raw = text.encode()
        anchor = {'id': 'cell', 'kind': 'text', 'text': needle, 'start': normalized.rindex(needle)}
        source = {'id': 'fixture-table', 'format': 'html', 'sha256': hashlib.sha256(raw).hexdigest(),
                  'bytes': len(raw), 'anchors': [anchor]}
        result = evidence_view(source, anchor, raw)
        self.assertTrue(result['table_id'].startswith('table-'))
        self.assertTrue(result['row_id'].startswith('tr-'))
        self.assertTrue(result['cell_id'].startswith('td-'))
        nodes = list(all_nodes(result['nodes']))
        self.assertEqual(''.join(x['text'] for x in nodes if x.get('marked')), '같은금액')
        self.assertIn(2, [x.get('rowspan') for x in nodes])
        self.assertIn(2, [x.get('colspan') for x in nodes])
        screen = json.dumps(nodes, ensure_ascii=False)
        self.assertIn('음수 (1,200)', screen)
        for unsafe in ('onclick', 'javascript:', '<script>', 'example.org', 'display:none'):
            self.assertNotIn(unsafe, screen)

    def test_pdf_duplicate_uses_verified_offset_and_multiline_boxes(self):
        import pymupdf
        with pymupdf.open() as doc:
            page = doc.new_page(width=300, height=240)
            page.insert_text((35, 42), 'Same amount')
            page.insert_text((35, 92), 'Same amount')
            page.insert_text((35, 112), '(1,200) million won')
            page.set_rotation(90)
            raw = doc.tobytes()
            normalized = compact(page.get_text())
        anchor = {'id': 'pdf:2', 'kind': 'text', 'text': 'Same amount (1,200) million won',
                  'start': normalized.rindex('Sameamount'), 'pdf_page': 1}
        source = {'id': 'fixture-pdf', 'format': 'pdf', 'sha256': hashlib.sha256(raw).hexdigest(),
                  'bytes': len(raw), 'anchors': [anchor]}
        result = evidence_view(source, anchor, raw)
        self.assertEqual((result['page_index'], result['width'], result['height'],
                          result['intrinsic_rotation']), (0, 300, 240, 90))
        self.assertEqual(len(result['boxes']), 2)
        self.assertGreater(result['boxes'][0][1], 70)
        self.assertGreater(result['boxes'][1][1], result['boxes'][0][1])
        with self.assertRaisesRegex(ValueError, 'original_hash_or_size_mismatch'):
            evidence_view(source, anchor, raw + b'changed')

    def test_route_rejects_other_version_cross_site_and_missing_original(self):
        pack, raw = fixture()
        pack['sources'][0]['title'] = 'Fixture'
        namespace = '11111111-1111-4111-8111-111111111111'
        _, _, catalog = build_indexes(pack, namespace)
        version, anchor = catalog[0]['version_id'], catalog[0]['anchors'][0]['id']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with ThreadingHTTPServer(('127.0.0.1', 0), app(0, root, root, pack, namespace)) as server:
                port = server.server_port
                server.RequestHandlerClass = app(port, root, root, pack, namespace)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                url = f'http://127.0.0.1:{port}'
                path = '/api/evidence/' + version + '/' + quote(anchor)
                try:
                    with self.assertRaises(HTTPError) as missing:
                        urlopen(url + path)
                    self.assertEqual(json.load(missing.exception)['error'], 'original_unavailable')
                    (root / pack['sources'][0]['cache_key']).write_bytes(raw)
                    with urlopen(url + path) as response:
                        self.assertEqual(json.load(response)['status'], 'text_verified')
                        self.assertIn("default-src 'none'", response.headers['Content-Security-Policy'])
                    with self.assertRaises(HTTPError) as incorrect:
                        urlopen(url + '/api/evidence/' + namespace + '/' + quote(anchor))
                    self.assertEqual(incorrect.exception.code, 404)
                    with self.assertRaises(HTTPError) as outside:
                        urlopen(Request(url + path, headers={'Sec-Fetch-Site': 'cross-site'}))
                    self.assertEqual(outside.exception.code, 403)
                finally:
                    server.shutdown()
                    worker.join()


if __name__ == '__main__':
    unittest.main()
