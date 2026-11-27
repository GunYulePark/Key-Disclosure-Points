"""Development-only original storage preflight/restore. Default: offline plan.

No key loading from files, no LLM/production/deployment, no original overwrite.
Hosted ingestion/bootstrap of DB memberships is a separate approved step.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import uuid
import warnings
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from case_pack import pack_fingerprint, validate_pack, verify_source
from central_contract import NAMESPACE, object_path, version_id

BUCKET = 'kdp-dev-originals'
MIMES = {'pdf': 'application/pdf', 'html': 'text/html',
         'hwp': 'application/x-hwp', 'jpg': 'image/jpeg'}


class SyncError(Exception):
    """Only safe error codes, never credentials or HTTP response bodies."""


def identity(source, workspace):
    # validate_pack already enforces approved research HTTPS hosts. UUID contract
    # is identical to central_contract, including existing official documents.
    uuid.UUID(workspace)
    doc = str(uuid.uuid5(NAMESPACE, source['url'] + '\n' + source['id']))
    ver = version_id(doc, source['sha256'])
    extension = 'jpeg' if source['format'] == 'jpg' else source['format']
    return {'document_id': doc, 'version_id': ver,
            'object_path': workspace + '/' + object_path(doc, source['sha256'], extension)}


def make_plan(pack, workspace, cache=None):
    validate_pack(pack)
    workspace = str(uuid.UUID(workspace))
    items = []
    for source in pack['sources']:
        if cache is not None:
            path = safe_target(cache, source['cache_key'])
            verify_source(source, path.read_bytes())
        items.append({'source_id': source['id'], 'sha256': source['sha256'],
                      'bytes': source['bytes'], 'cache_key': source['cache_key'],
                      'mime_type': MIMES[source['format']], **identity(source, workspace)})
    return {'pack_fingerprint': pack_fingerprint(pack), 'workspace_id': workspace,
            'bucket_id': BUCKET, 'sources': len(items),
            'bytes': sum(s['bytes'] for s in items), 'items': items,
            'local_originals_verified': cache is not None, 'cloud_writes': 0,
            'transfer_approved': False}


def safe_target(root, key):
    if not re.fullmatch(r'[0-9a-f]{64}\.(pdf|html|hwp|jpg)', key):
        raise SyncError('invalid_cache_key')
    root = Path(root).resolve()
    target = root / key
    if target.is_symlink() or target.resolve().parent != root:
        raise SyncError('cache_path_escape')
    return target


def target_config(config, env):
    """No automatic selection of a project because its name looks relevant."""
    ref = env.get('SUPABASE_DEV_PROJECT_REF', '')
    if env.get('APP_ENV') != 'development' or env.get('CENTRAL_STORE_MODE') != 'supabase':
        raise SyncError('development_connection_disabled')
    if not re.fullmatch('[a-z]{20}', ref):
        raise SyncError('invalid_project_ref')
    if (config.get('purpose') != 'kdp-development' or config.get('project_ref') != ref
            or config.get('approved') is not True):
        raise SyncError('approved_development_target_required')
    expected = f'https://{ref}.supabase.co'
    if env.get('SUPABASE_DEV_URL') != expected:
        raise SyncError('project_url_mismatch')
    workspace = str(uuid.UUID(env.get('SUPABASE_DEV_WORKSPACE_ID', '')))
    if config.get('workspace_id') != workspace:
        raise SyncError('workspace_mismatch')
    if env.get('SUPABASE_DEV_STORAGE_BUCKET', BUCKET) != BUCKET:
        raise SyncError('private_development_bucket_required')
    return expected, workspace


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncError('unexpected_http_redirect')


class Client:
    def __init__(self, config, env=None):
        env = os.environ if env is None else env
        self.url, self.workspace = target_config(config, env)
        self.key = env.get('SUPABASE_DEV_PUBLISHABLE_KEY', '')
        self.token = env.get('SUPABASE_DEV_ACCESS_TOKEN', '')
        self.secret = env.get('SUPABASE_DEV_SECRET_KEY', '')
        self.opener = build_opener(NoRedirect())

    def request(self, path, *, method='GET', body=None, server=False, content_type=None):
        password_login = path == '/auth/v1/token?grant_type=password' and method == 'POST'
        auth_user = path == '/auth/v1/user' and method == 'GET'
        if (not path.startswith(('/rest/v1/', '/storage/v1/'))
                and not (password_login or auth_user)) or '..' in path or '#' in path:
            raise SyncError('invalid_api_path')
        if server:
            if not self.secret:
                raise SyncError('server_credential_required')
            headers = {'apikey': self.secret}
            # Legacy service_role JWT compatibility; new sb_secret keys are not JWTs.
            if self.secret.count('.') == 2:
                headers['Authorization'] = 'Bearer ' + self.secret
        elif password_login:
            if not self.key:
                raise SyncError('publishable_key_required')
            headers = {'apikey': self.key}
        else:
            if not self.key or not self.token:
                raise SyncError('authenticated_reader_credentials_required')
            headers = {'apikey': self.key, 'Authorization': 'Bearer ' + self.token}
        raw = body if isinstance(body, bytes) else json.dumps(body).encode() if body is not None else None
        if raw is not None:
            headers['Content-Type'] = content_type or 'application/json'
        try:
            with self.opener.open(Request(self.url + path, data=raw, method=method,
                                          headers=headers), timeout=60) as response:
                raw = response.read(10 * 1024 * 1024 + 1)
                if len(raw) > 10 * 1024 * 1024:
                    raise SyncError('response_size_limit')
                return raw
        except HTTPError as exc:
            raise SyncError(f'http_{exc.code}') from None
        except (URLError, TimeoutError, OSError):
            raise SyncError('network_failure') from None

    def json(self, path, **kwargs):
        return json.loads(self.request(path, **kwargs))

    def sign_in_with_password(self, email, password):
        response = self.json('/auth/v1/token?grant_type=password', method='POST',
                             body={'email': email, 'password': password})
        token = response.get('access_token')
        if not isinstance(token, str) or not token:
            raise SyncError('auth_session_not_available')
        self.token = token
        return response.get('expires_in')

    def download_original(self, source):
        """Read with the current user's Storage policies and verify bytes."""
        item = identity(source, self.workspace)
        raw = self.request('/storage/v1/object/authenticated/' + BUCKET + '/'
                           + quote(item['object_path'], safe='/'))
        if len(raw) != source['bytes'] or hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('original_hash_or_size_mismatch')
        return raw

    def check_workspace(self):
        user = self.json('/auth/v1/user')
        if user.get('is_anonymous') is True:
            raise SyncError('permanent_auth_user_required')
        user_id = str(uuid.UUID(user['id']))
        members = self.json('/rest/v1/kdp_workspace_members?select=member_role'
                            f'&workspace_id=eq.{self.workspace}&user_id=eq.{user_id}')
        if len(members) != 1 or members[0]['member_role'] not in ('owner', 'editor', 'viewer'):
            raise SyncError('approved_workspace_membership_required')
        rows = self.json('/rest/v1/kdp_workspaces?select=id'
                         f'&id=eq.{self.workspace}')
        if rows != [{'id': self.workspace}]:
            raise SyncError('approved_workspace_not_visible')
        return {'workspace_visible': True, 'member_role': members[0]['member_role'],
                'bucket_id': BUCKET, 'cloud_data_writes': 0}

    def check_bucket(self, *, create=False):
        path = '/storage/v1/bucket/' + BUCKET
        try:
            bucket = self.json(path, server=True)
        except SyncError as exc:
            if not create or str(exc) != 'http_404':
                raise
            self.request('/storage/v1/bucket', method='POST', server=True,
                         body={'id': BUCKET, 'name': BUCKET, 'public': False,
                               'fileSizeLimit': 10 * 1024 * 1024,
                               'allowedMimeTypes': list(MIMES.values())})
            bucket = self.json(path, server=True)
        # Never silently make an existing public bucket private or adopt it.
        if bucket.get('id') != BUCKET or bucket.get('public') is not False:
            raise SyncError('bucket_is_not_private_development_bucket')
        return {'bucket_id': BUCKET, 'private': True}

    def restore(self, pack, destination, source_ids=None):
        plan = make_plan(pack, self.workspace)
        if source_ids and not set(source_ids) <= {source['id'] for source in pack['sources']}:
            raise SyncError('requested_source_not_in_pack')
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        restored, cached, selected = 0, 0, 0
        for source, item in zip(pack['sources'], plan['items']):
            if source_ids and source['id'] not in source_ids:
                continue
            selected += 1
            path = safe_target(destination, source['cache_key'])
            if path.exists():
                verify_source(source, path.read_bytes())
                cached += 1
                continue
            filters = ('workspace_id=eq.' + self.workspace + '&document_version_id=eq.'
                       + item['version_id'] + '&select=object_path,sha256,byte_length,verification_status')
            rows = self.json('/rest/v1/kdp_document_files?' + filters)
            expected = {'object_path': item['object_path'], 'sha256': item['sha256'],
                        'byte_length': item['bytes'], 'verification_status': 'verified'}
            if expected not in rows:
                raise SyncError('verified_file_manifest_not_available')
            raw = self.download_original(source)
            verify_source(source, raw)
            # Exclusive create preserves concurrent workers and existing bytes.
            # Each retry verifies the cached file; partial writes cannot pass.
            try:
                with path.open('xb') as stream:
                    stream.write(raw)
            except FileExistsError:
                verify_source(source, path.read_bytes())
                cached += 1
                continue
            restored += 1
        return {'restored': restored, 'cached_verified': cached, 'sources': selected,
                'cloud_writes': 0, 'hosted_validation_claimed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'bucket', 'check', 'restore'],
                        nargs='?', default='plan')
    parser.add_argument('--pack', type=Path, default=Path('research/priority-case-pack-v2.json'))
    parser.add_argument('--workspace', help='Approved UUID; required for offline plan')
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--source', action='append', help='Limit restore to this source ID. Repeat as needed.')
    parser.add_argument('--target', type=Path, help='Ignored local approved-target JSON, no keys')
    parser.add_argument('--apply', action='store_true', help='Explicit bucket creation only')
    parser.add_argument('--password-login', action='store_true',
                        help='Prompt for an existing project Auth account without saving the password or token')
    parser.add_argument('--output', type=Path, help='Optional local plan JSON (not a transfer approval)')
    args = parser.parse_args()
    if args.apply and args.action != 'bucket':
        parser.error('--apply is supported only with bucket')
    if args.password_login and args.action not in ('check', 'restore'):
        parser.error('--password-login is supported only with check or restore')
    if args.source and args.action != 'restore':
        parser.error('--source is supported only with restore')
    if args.action != 'plan':
        if not args.target:
            parser.error('--target is required')
        client = Client(json.loads(args.target.read_text(encoding='utf-8-sig')))
        if args.password_login:
            if not sys.stdin.isatty():
                raise SyncError('interactive_terminal_required')
            email = input('Supabase project Auth email: ').strip()
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                try:
                    password = getpass.getpass('Supabase project Auth password: ')
                except getpass.GetPassWarning:
                    raise SyncError('hidden_password_input_unavailable') from None
            client.sign_in_with_password(email, password)
            del password
    if args.action == 'bucket':
        result = client.check_bucket(create=args.apply)
    elif args.action == 'check':
        result = client.check_workspace()
    else:
        pack = json.loads(args.pack.read_text(encoding='utf-8-sig'))
        if args.action == 'plan':
            if not args.workspace:
                parser.error('--workspace is required')
            result = make_plan(pack, args.workspace, args.cache)
        else:
            if not args.cache:
                parser.error('--cache is required for restore')
            result = client.restore(pack, args.cache, args.source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != 'items'}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except SyncError as exc:
        print('central_sync_failed: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
    except (ValueError, KeyError, OSError, TypeError):
        print('central_sync_failed: check target, credentials, manifest and original hashes', file=sys.stderr)
        raise SystemExit(1)
