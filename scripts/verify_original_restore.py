"""One-time, local-only verification of an authenticated Supabase restore."""
from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote
from urllib.request import Request

from central_ingest import read_json
from central_sync import BUCKET, Client, SyncError, identity


def verify(client, pack, report_folder, source_ids):
    workspace = client.check_workspace()
    with tempfile.TemporaryDirectory(prefix='viewer-restore-', dir=report_folder) as folder:
        restored = client.restore(pack, folder, source_ids)
        if restored['restored'] != len(source_ids) or restored['cached_verified']:
            raise SyncError('restore_did_not_read_every_object_remotely')
        selected = [s for s in pack['sources'] if s['id'] in source_ids]
        denied = 0
        for source in selected:
            key = quote(identity(source, client.workspace)['object_path'], safe='/')
            request = Request(client.url + f'/storage/v1/object/public/{BUCKET}/{key}',
                              headers={'apikey': client.key})
            try:
                with client.opener.open(request, timeout=15):
                    raise SyncError('public_request_unexpectedly_succeeded')
            except HTTPError as exc:
                if exc.code not in {400, 401, 403, 404}:
                    raise SyncError(f'public_request_unexpected_http_{exc.code}') from None
                denied += 1
            except URLError:
                raise SyncError('public_request_could_not_be_checked') from None
        return {'authenticated_workspace': workspace['workspace_visible'],
                'member_role': workspace['member_role'], 'restored': restored['restored'],
                'public_denied': denied, 'bytes_verified': sum(s['bytes'] for s in selected),
                'text_anchors_verified': sum(a['kind'] == 'text' for s in selected for a in s['anchors']),
                'sources': sorted(source_ids)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--pack', type=Path, default=Path('research/priority-case-pack-v2.json'))
    parser.add_argument('--source', action='append', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    config, pack = read_json(args.target), read_json(args.pack)
    source_ids = set(args.source)
    if not source_ids <= {s['id'] for s in pack['sources']}:
        parser.error('unknown source ID')
    client = Client(config)
    if not client.key:
        parser.error('SUPABASE_DEV_PUBLISHABLE_KEY is required')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.report.exists():
        parser.error('use a new local report path')
    token = secrets.token_urlsafe(32)
    origin = f'http://127.0.0.1:{args.port}'
    completed = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, title, content, status=200):
            page = f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{font:17px system-ui;background:#f2f5f8;color:#153049;max-width:42rem;margin:10vh auto;padding:1.5rem}}main{{background:white;border:1px solid #ccd9e4;padding:1.8rem}}label{{display:block;margin-top:1rem}}input{{display:block;width:95%;padding:.65rem;margin-top:.35rem}}button{{font:inherit;padding:.7rem 1rem;margin-top:1rem;background:#153d58;color:white;border:0}}code{{overflow-wrap:anywhere}}</style>
<main><h1>{title}</h1>{content}</main></html>""".encode()
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(page)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(page)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{args.port}'

        def do_GET(self):
            if self.path != '/' or not self.valid_host():
                self.send_error(404)
                return
            self.reply('비공개 원본 복원 검사', f"""
<p>개발 프로젝트의 Auth 사용자로 로그인해 법령 원본 {len(source_ids)}개를 확인합니다.</p>
<form method="post" action="/verify" autocomplete="off">
<input type="hidden" name="csrf" value="{token}">
<label>프로젝트 Auth 이메일<input name="email" type="email" required autocomplete="off"></label>
<label>비밀번호<input name="password" type="password" required autocomplete="off"></label>
<button>로그인 및 원본 복원 확인</button></form>""")

        def do_POST(self):
            nonlocal completed
            if (self.path != '/verify' or not self.valid_host()
                    or self.headers.get('Origin') != origin):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size < 8192:
                    raise ValueError()
                fields = parse_qs(self.rfile.read(size).decode(), strict_parsing=True, max_num_fields=3)
                if not secrets.compare_digest(fields['csrf'][0], token):
                    raise ValueError()
                client.sign_in_with_password(fields['email'][0], fields['password'][0])
                result = verify(client, pack, args.report.parent, source_ids)
                with args.report.open('x', encoding='utf8') as stream:
                    json.dump(result, stream, ensure_ascii=False, indent=2)
                completed = True
                self.reply('복원 검사 완료', '<p>원본 해시와 인용 위치가 일치합니다. 이 창을 닫아도 됩니다.</p>')
            except SyncError as exc:
                self.reply('복원 검사 실패', f'<p><code>{html.escape(str(exc))}</code></p><p><a href="/">다시 시도</a></p>', 400)
            except (KeyError, ValueError, OSError):
                self.reply('복원 검사 실패', '<p>입력 또는 원본 검증 오류입니다.</p><p><a href="/">다시 시도</a></p>', 400)
            finally:
                client.token = ''

    with HTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.timeout = 1
        print(origin, flush=True)
        deadline = time.monotonic() + 1200
        while not completed and time.monotonic() < deadline:
            server.handle_request()
    if not completed:
        raise SystemExit('restore verification timed out')


if __name__ == '__main__':
    main()
