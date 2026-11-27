"""Read approved evidence using the signed-in project's Auth token and RLS."""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlencode

from central_ingest import stable_id
from central_sync import BUCKET, MIMES, Client, SyncError, identity
from evidence_locations import EXTRACTOR_VERSION, canonical_location


def reader_rows(client, table, columns, **filters):
    query = urlencode({'select': columns, 'workspace_id': 'eq.' + client.workspace, **filters})
    rows = client.json(f'/rest/v1/{table}?{query}')
    if not isinstance(rows, list):
        raise SyncError('cloud_response_invalid')
    return rows


def file_matches(source, client, row):
    expected = identity(source, client.workspace)
    return (row['document_version_id'] == expected['version_id']
            and row['bucket_id'] == BUCKET and row['object_path'] == expected['object_path']
            and row['sha256'] == source['sha256'] and row['byte_length'] == source['bytes']
            and row['mime_type'] == MIMES[source['format']] and row['verification_status'] == 'verified')


def anchor_matches(anchor, row):
    return (row['legacy_evidence_id'] == anchor['id'] and row['kind'] == anchor['kind']
            and row['exact_text'] == anchor.get('text')
            and row['normalized_text_start'] == anchor.get('start')
            and row['page_index'] == (anchor['pdf_page'] - 1 if 'pdf_page' in anchor else None)
            and row['location_note'] == anchor.get('location')
            and row['verification_status'] == ('text_verified' if anchor['kind'] == 'text' else 'manually_verified'))


FILE_COLUMNS = 'document_version_id,bucket_id,object_path,sha256,byte_length,mime_type,verification_status'
ANCHOR_COLUMNS = 'document_version_id,legacy_evidence_id,kind,exact_text,normalized_text_start,page_index,location_note,verification_status'


def ready_versions(client, **filters):
    return reader_rows(client, 'kdp_document_versions', 'id,document_id,sha256,byte_length,version_label',
                       processing_status='eq.ready', **filters)


def version_matches(source, client, row):
    item = identity(source, client.workspace)
    return (row['id'] == item['version_id'] and row['document_id'] == item['document_id']
            and row['sha256'] == source['sha256'] and row['byte_length'] == source['bytes']
            and row['version_label'] == source['version_label'])


def catalog_for(client, sources, anchors, catalog):
    client.check_workspace()
    versions = {row['id']: row for row in ready_versions(client)}
    if not versions:
        return []
    files = reader_rows(client, 'kdp_document_files', FILE_COLUMNS, verification_status='eq.verified')
    approvals = {row['id']: row['source_url'] for row in reader_rows(
        client, 'kdp_sources', 'id,source_url', rights_status='eq.permitted', transfer_approved='eq.true')}
    citations = {(row['document_version_id'], row['legacy_evidence_id']): row
                 for row in reader_rows(client, 'kdp_evidence_spans', ANCHOR_COLUMNS)}
    visible = []
    for document in catalog:
        version = document['version_id']
        source = sources[version]
        if (version not in versions or not version_matches(source, client, versions[version])
                or approvals.get(stable_id('source', source['url'])) != source['url']
                or not any(file_matches(source, client, row) for row in files)):
            continue
        confirmed = [
            entry for entry in document['anchors']
            if (key := (version, entry['id'])) in citations and anchor_matches(anchors[key], citations[key])
        ]
        if confirmed:
            visible.append({**document, 'anchors': confirmed})
    return visible


def load_original(client, source, version, anchor=None):
    versions = ready_versions(client, id='eq.' + version)
    if len(versions) != 1 or not version_matches(source, client, versions[0]):
        raise FileNotFoundError()
    files = reader_rows(client, 'kdp_document_files', FILE_COLUMNS,
                        document_version_id='eq.' + version, verification_status='eq.verified')
    if not any(file_matches(source, client, row) for row in files):
        raise FileNotFoundError()
    if anchor:
        citations = reader_rows(client, 'kdp_evidence_spans', ANCHOR_COLUMNS,
                                document_version_id='eq.' + version, legacy_evidence_id='eq.' + anchor['id'])
        if len(citations) != 1:
            raise FileNotFoundError()
        if not anchor_matches(anchor, citations[0]):
            raise ValueError('cloud_anchor_mismatch')
    # The storage policy independently checks current source approval and membership.
    return client.download_original(source)


def check_saved_location(client, source, version, anchor, view):
    try:
        saved = reader_rows(client, 'kdp_evidence_locations', 'sha256,byte_length,location',
                            document_version_id='eq.' + version, legacy_evidence_id='eq.' + anchor['id'],
                            extractor_version='eq.' + EXTRACTOR_VERSION)
    except SyncError as error:
        if str(error) == 'http_404':
            # Older development databases can still render a verified original.
            return 'source_verified'
        raise
    if not saved:
        return 'source_verified'
    expected = {'sha256': source['sha256'], 'byte_length': source['bytes'],
                'location': canonical_location(view)}
    if saved != [expected]:
        raise ValueError('saved_location_mismatch')
    return 'db_matched'


@dataclass(frozen=True)
class Session:
    client: Client
    expires_at: float


class ViewerSessions:
    """Process-local viewer sessions. No refresh token, disk storage or service key."""
    def __init__(self, config, env, *, client_factory=Client, clock=time.monotonic):
        self.config = config
        self.env = {name: value for name, value in env.items()
                    if name in {'APP_ENV', 'CENTRAL_STORE_MODE', 'SUPABASE_DEV_PROJECT_REF',
                                'SUPABASE_DEV_URL', 'SUPABASE_DEV_WORKSPACE_ID',
                                'SUPABASE_DEV_STORAGE_BUCKET', 'SUPABASE_DEV_PUBLISHABLE_KEY'}}
        self.client_factory = client_factory
        self.company_signins = {}
        for default_id, company in {'ckd': 'ckd', 'ckdhd': 'hold', 'kbp': 'kb'}.items():
            prefix = 'KDP_SIGNIN_' + default_id.upper()
            login_id = (env.get(prefix + '_ID') or default_id).strip().lower()
            if not login_id or not login_id.isascii() or not login_id.isalnum() or login_id in self.company_signins:
                raise SyncError('invalid_company_login_ids')
            self.company_signins[login_id] = (company, env.get(prefix + '_EMAIL', '').strip())
        self.clock = clock
        self.csrf = secrets.token_urlsafe(32)
        self.entries: dict[str, Session] = {}
        self.lock = Lock()
        if not self.client_factory(config, self.env).key:
            raise SyncError('publishable_key_required')

    def login(self, identifier, password):
        company = None
        email = identifier
        if '@' not in identifier:
            alias = self.company_signins.get(identifier.lower())
            if alias is None or '@' not in alias[1]:
                raise SyncError('auth_signin_failed')
            company, email = alias
        client = self.client_factory(self.config, self.env)
        expires_in = client.sign_in_with_password(email, password)
        if type(expires_in) is not int or expires_in <= 5:
            raise SyncError('auth_session_not_available')
        membership = client.check_workspace()
        if company is not None and membership.get('intake_company_id') != company:
            raise SyncError('approved_workspace_membership_required')
        ttl = min(1800, expires_in - 5)
        session_id = secrets.token_urlsafe(32)
        with self.lock:
            now = self.clock()
            self.entries = {key: entry for key, entry in self.entries.items() if entry.expires_at > now}
            while len(self.entries) >= 16:
                self.entries.pop(next(iter(self.entries)))
            self.entries[session_id] = Session(client, now + ttl)
        return session_id, ttl

    def get(self, identifier):
        with self.lock:
            entry = self.entries.get(identifier)
            if entry and entry.expires_at > self.clock():
                return entry.client
            self.entries.pop(identifier, None)
        return None

    def remove(self, identifier):
        with self.lock:
            self.entries.pop(identifier, None)
