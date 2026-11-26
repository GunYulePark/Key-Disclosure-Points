"""Serve the private development evidence preview on this computer only."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from case_pack import validate_pack
from central_ingest import read_json
from central_sync import SyncError, identity, safe_target
from evidence_view import evidence_view


def build_indexes(pack, workspace):
    validate_pack(pack)
    sources, anchors, catalog = {}, {}, []
    for source in pack['sources']:
        version = identity(source, workspace)['version_id']
        sources[version] = source
        entries = []
        for anchor in source['anchors']:
            anchors[(version, anchor['id'])] = anchor
            entries.append({'id': anchor['id'], 'label': anchor.get('text', anchor.get('location')),
                            'page': anchor.get('pdf_page'), 'kind': anchor['kind']})
        catalog.append({'id': source['id'], 'version_id': version, 'title': source['title'],
                        'version_label': source['version_label'], 'format': source['format'],
                        'anchors': entries})
    return sources, anchors, catalog


def verified_bytes(cache, source):
    path = safe_target(cache, source['cache_key'])
    if path.stat().st_size != source['bytes']:
        raise ValueError('original_hash_or_size_mismatch')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('original_hash_or_size_mismatch')
    return data


def app(port, site, cache, pack, workspace):
    sources, anchors, catalog = build_indexes(pack, workspace)
    host = f'127.0.0.1:{port}'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, raw, mime, status=200, *, filename=None):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; "
                             "worker-src 'self' blob:; connect-src 'self'; img-src 'self' blob: data:; "
                             "style-src 'self' 'unsafe-inline'; font-src 'self' blob:; frame-ancestors 'none'; "
                             "form-action 'none'; base-uri 'none'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(raw)

        def json(self, payload, status=200):
            self.send(json.dumps(payload, ensure_ascii=False).encode(), 'application/json; charset=utf-8', status)

        def do_GET(self):
            if self.headers.get('Host') != host or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.json({'error': 'local_origin_required'}, 403)
                return
            path = urlsplit(self.path).path
            parts = [unquote(part) for part in path.split('/')[1:]]
            try:
                if path == '/api/catalog':
                    self.json({'sources': catalog})
                elif len(parts) == 4 and parts[:2] == ['api', 'evidence']:
                    version, anchor_id = parts[2:]
                    source = sources[version]
                    anchor = anchors[(version, anchor_id)]
                    data = verified_bytes(cache, source)
                    view = evidence_view(source, anchor, data)
                    self.json({'source_id': source['id'], 'version_id': version, 'anchor_id': anchor_id,
                               'title': source['title'], 'format': source['format'],
                               'source_url': source['url'], 'version_label': source['version_label'],
                               'sha256': source['sha256'], 'bytes': source['bytes'],
                               'raw_url': '/api/original/' + version, **view})
                elif len(parts) == 3 and parts[:2] == ['api', 'original']:
                    version = parts[2]
                    source = sources[version]
                    data = verified_bytes(cache, source)
                    mime = 'image/jpeg' if source['format'] == 'jpg' else 'application/octet-stream'
                    self.send(data, mime, filename=source['cache_key'])
                elif path == '/' or parts[0] in ('assets', 'vendor'):
                    file = (site / ('index.html' if path == '/' else '/'.join(parts))).resolve()
                    if not file.is_relative_to(site) or not file.is_file():
                        raise KeyError()
                    mime = {'.mjs': 'application/javascript', '.js': 'application/javascript',
                            '.wasm': 'application/wasm'}.get(file.suffix, mimetypes.guess_type(file.name)[0])
                    self.send(file.read_bytes(), mime or 'application/octet-stream')
                else:
                    raise KeyError()
            except KeyError:
                self.json({'error': 'version_or_anchor_not_found'}, 404)
            except FileNotFoundError:
                self.json({'error': 'original_unavailable'}, 404)
            except (SyncError, ValueError, RuntimeError, RecursionError):
                self.json({'error': 'original_or_anchor_verification_failed'}, 422)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--site', type=Path, default=Path('.local/task02/site'))
    parser.add_argument('--cache', type=Path, default=Path('.local/case-research/originals'))
    parser.add_argument('--pack', type=Path, default=Path('research/priority-case-pack-v2.json'))
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    site = args.site.resolve()
    if not (site / 'index.html').is_file():
        parser.error('build the preview first: node scripts/build-evidence.mjs')
    target = read_json(args.target)
    if target.get('purpose') != 'kdp-development' or target.get('approved') is not True:
        parser.error('approved development target required')
    with ThreadingHTTPServer(('127.0.0.1', args.port),
                             app(args.port, site, args.cache.resolve(), read_json(args.pack),
                                 target['workspace_id'])) as server:
        print(f'http://127.0.0.1:{args.port}/', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
