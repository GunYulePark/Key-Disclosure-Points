"""Serve the private development evidence preview on this computer only."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import secrets
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from case_pack import validate_pack
from central_ingest import read_json
from central_sync import SyncError, identity, safe_target
from evidence_cloud import ViewerSessions, catalog_for, check_saved_location, load_original
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


def app(port, site, cache, pack, workspace, sessions=None):
    sources, anchors, catalog = build_indexes(pack, workspace)
    host = f'127.0.0.1:{port}'
    origin = 'http://' + host
    cookie_name = f'kdp_viewer_{port}'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, raw, mime, status=200, *, filename=None, cookie=None):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Referrer-Policy', 'same-origin')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; "
                             "worker-src 'self' blob:; connect-src 'self'; img-src 'self' blob: data:; "
                             "style-src 'self' 'unsafe-inline'; font-src 'self' blob:; frame-ancestors 'none'; "
                             "form-action 'none'; base-uri 'none'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            if cookie is not None:
                identifier, ttl = cookie
                self.send_header('Set-Cookie',
                                 f'{cookie_name}={identifier}; Max-Age={ttl}; Path=/api; HttpOnly; SameSite=Strict')
            self.end_headers()
            self.wfile.write(raw)

        def json(self, payload, status=200, *, cookie=None):
            self.send(json.dumps(payload, ensure_ascii=False).encode(), 'application/json; charset=utf-8',
                      status, cookie=cookie)

        def local_request(self):
            return (self.headers.get('Host') == host
                    and self.headers.get('Sec-Fetch-Site') in (None, 'none', 'same-origin'))

        def session_id(self):
            try:
                cookie = SimpleCookie(self.headers.get('Cookie', '')).get(cookie_name)
                return cookie.value if cookie else ''
            except CookieError:
                return ''

        def session_state(self, signed_in=False):
            if sessions is None:
                return {'mode': 'cache', 'signed_in': True}
            return {'mode': 'supabase', 'signed_in': signed_in, 'csrf': sessions.csrf}

        def do_POST(self):
            if (not self.local_request() or self.headers.get('Origin') != origin
                    or sessions is None or not secrets.compare_digest(
                        self.headers.get('X-KDP-CSRF', '').encode('utf8'), sessions.csrf.encode('ascii'))):
                self.json({'error': 'local_origin_required'}, 403)
                return
            if self.path == '/api/session/logout':
                sessions.remove(self.session_id())
                self.json(self.session_state(), cookie=('', 0))
                return
            if self.path != '/api/session':
                self.json({'error': 'unknown_action'}, 404)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size < 8192 or self.headers.get_content_type() != 'application/json':
                    raise ValueError()
                payload = json.loads(self.rfile.read(size))
                email, password = payload['email'], payload['password']
                if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password:
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                self.json({'error': 'invalid_login_form'}, 400)
                return
            try:
                cookie = sessions.login(email.strip(), password)
            except SyncError as error:
                code = str(error)
                if code in {'http_400', 'http_401', 'http_403', 'auth_session_not_available'}:
                    self.json({'error': 'auth_signin_failed'}, 401)
                elif code in {'approved_workspace_membership_required', 'approved_workspace_not_visible',
                              'permanent_auth_user_required'}:
                    self.json({'error': 'workspace_access_denied'}, 403)
                else:
                    self.json({'error': 'cloud_request_failed'}, 502)
                return
            except (KeyError, TypeError, ValueError):
                self.json({'error': 'cloud_request_failed'}, 502)
                return
            sessions.remove(self.session_id())
            self.json(self.session_state(signed_in=True), cookie=cookie)

        def do_GET(self):
            path = urlsplit(self.path).path
            # A click from the chat may navigate cross-site to the static entry.
            # The entry contains no data; its subsequent API calls stay same-origin.
            public_entry = path == '/' and self.headers.get('Host') == host
            if not public_entry and not self.local_request():
                self.json({'error': 'local_origin_required'}, 403)
                return
            parts = [unquote(part) for part in path.split('/')[1:]]
            user = sessions.get(self.session_id()) if sessions and path.startswith('/api/') else None
            if path == '/api/session':
                self.json(self.session_state(signed_in=user is not None))
                return
            if sessions and path.startswith('/api/') and user is None:
                self.json({'error': 'auth_required'}, 401, cookie=('', 0))
                return
            try:
                if path == '/api/catalog':
                    visible = catalog_for(user, sources, anchors, catalog) if sessions else catalog
                    self.json({'sources': visible})
                elif len(parts) == 4 and parts[:2] == ['api', 'evidence']:
                    version, anchor_id = parts[2:]
                    source = sources[version]
                    anchor = anchors[(version, anchor_id)]
                    data = load_original(user, source, version, anchor) if sessions else verified_bytes(cache, source)
                    view = evidence_view(source, anchor, data)
                    location_check = (check_saved_location(user, source, version, anchor, view)
                                      if sessions else 'source_verified')
                    self.json({'source_id': source['id'], 'version_id': version, 'anchor_id': anchor_id,
                               'title': source['title'], 'format': source['format'],
                               'source_url': source['url'], 'version_label': source['version_label'],
                               'sha256': source['sha256'], 'bytes': source['bytes'],
                               'raw_url': '/api/original/' + version, 'location_check': location_check, **view})
                elif len(parts) == 3 and parts[:2] == ['api', 'original']:
                    version = parts[2]
                    source = sources[version]
                    data = load_original(user, source, version) if sessions else verified_bytes(cache, source)
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
            except SyncError as error:
                code = str(error)
                if sessions and code == 'http_401':
                    sessions.remove(self.session_id())
                    self.json({'error': 'auth_required'}, 401, cookie=('', 0))
                elif sessions and code in {'approved_workspace_membership_required',
                                           'approved_workspace_not_visible', 'permanent_auth_user_required',
                                           'http_403'}:
                    sessions.remove(self.session_id())
                    self.json({'error': 'workspace_access_denied'}, 403, cookie=('', 0))
                elif sessions and code in {'http_400', 'http_404'}:
                    self.json({'error': 'original_unavailable'}, 404)
                elif sessions:
                    self.json({'error': 'cloud_request_failed'}, 502)
                else:
                    self.json({'error': 'original_or_anchor_verification_failed'}, 422)
            except (ValueError, RuntimeError, RecursionError):
                self.json({'error': 'original_or_anchor_verification_failed'}, 422)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--site', type=Path, default=Path('.local/task02/site'))
    parser.add_argument('--cache', type=Path, default=Path('.local/case-research/originals'))
    parser.add_argument('--pack', type=Path, default=Path('research/priority-case-pack-v2.json'))
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--cloud', action='store_true', help='Require Supabase Auth and read from private Storage')
    args = parser.parse_args()
    site = args.site.resolve()
    if not (site / 'index.html').is_file():
        parser.error('build the preview first: node scripts/build-evidence.mjs')
    target = read_json(args.target)
    if target.get('purpose') != 'kdp-development' or target.get('approved') is not True:
        parser.error('approved development target required')
    try:
        sessions = ViewerSessions(target, os.environ) if args.cloud else None
    except (SyncError, ValueError) as error:
        parser.error(str(error))
    with ThreadingHTTPServer(('127.0.0.1', args.port),
                             app(args.port, site, args.cache.resolve(), read_json(args.pack),
                                 target['workspace_id'], sessions)) as server:
        print(f'http://127.0.0.1:{args.port}/', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
