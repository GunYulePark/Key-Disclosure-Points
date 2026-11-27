"""Authenticated development intake using the existing project and private bucket."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from urllib.parse import urlencode, urlsplit, urlunsplit

from central_sync import BUCKET, SyncError
from evidence_cloud import reader_rows
from intake_context import candidate_cases, case_links

PDF_LIMIT = 10 * 1024 * 1024
PAGE_SIZE = 40
ENTRY_COLUMNS = 'id,kind,title,company_id,source_url,rights_basis,sha256,byte_length,created_at,stored_at,origin_format'
SITE_COLUMNS = 'url,title,category,note,created_at'


def field(payload, name, length, *, optional=False):
    value = payload.get(name, '')
    if not isinstance(value, str) or '\x00' in value or len(value.strip()) > length:
        raise ValueError('invalid_intake')
    value = value.strip()
    if not value and not optional:
        raise ValueError('invalid_intake')
    return value


def source_url(value):
    if not value:
        return None
    try:
        url = urlsplit(value)
        if (url.scheme != 'https' or not url.hostname or url.username is not None
                or url.password is not None or url.port not in (443, None)
                or re.search(r'[\s\\\x00-\x1f\x7f]', value)):
            raise ValueError()
        authority = url.hostname.encode('idna').decode('ascii').lower()
        if not re.fullmatch(r'[a-z0-9.-]+', authority):
            raise ValueError()
        normalized = urlunsplit((url.scheme, authority, url.path or '/', url.query, url.fragment))
        if len(normalized) > 1024:
            raise ValueError()
        return normalized
    except ValueError:
        raise ValueError('invalid_intake_url') from None


def intake_list(client, page=1):
    offset = str((page - 1) * PAGE_SIZE)
    options = dict(limit=str(PAGE_SIZE + 1), offset=offset)
    entries = reader_rows(client, 'kdp_intake_entries', ENTRY_COLUMNS, order='created_at.desc,id.desc', **options)
    sites = reader_rows(client, 'kdp_reference_sites', SITE_COLUMNS, order='created_at.desc,url.asc', **options)
    return {'entries': entries[:PAGE_SIZE], 'sites': sites[:PAGE_SIZE],
            'has_more': len(entries) > PAGE_SIZE or len(sites) > PAGE_SIZE,
            'can_write': client.check_workspace()['member_role'] in ('owner', 'editor')}


def entry(client, entry_id, *, detail=False):
    entry_id = str(uuid.UUID(entry_id))
    columns = ENTRY_COLUMNS + (',body_text,object_path' if detail else '')
    rows = reader_rows(client, 'kdp_intake_entries', columns, id='eq.' + entry_id)
    if not rows:
        raise FileNotFoundError()
    return rows[0]


def add_site(client, payload):
    category = field(payload, 'category', 20)
    if category not in ('filing', 'regulation', 'guidance', 'other'):
        raise ValueError('invalid_intake')
    item = {'workspace_id': client.workspace, 'url': source_url(field(payload, 'url', 1024)),
            'title': field(payload, 'title', 160), 'category': category,
            'note': field(payload, 'note', 500, optional=True)}
    try:
        client.request('/rest/v1/kdp_reference_sites', method='POST', body=item)
    except SyncError as error:
        if str(error) != 'http_409':
            raise
        return {'existing': True}
    return {'existing': False}


def checked_pdf(client, item):
    path = '/storage/v1/object/authenticated/' + BUCKET + '/' + item['object_path']
    raw = client.request(path)
    if len(raw) != item['byte_length'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('intake_integrity_failed')
    return raw


def file_for(client, entry_id):
    item = entry(client, entry_id, detail=True)
    if item['kind'] != 'pdf' or not item['stored_at']:
        raise FileNotFoundError()
    return checked_pdf(client, item)


def notes_for(client, entry_id):
    rows = reader_rows(client, 'kdp_intake_notes', 'id,points,related_case_ids,created_at',
                       intake_id='eq.' + entry_id, order='created_at.desc,id.desc', limit='40')
    return [dict(note, related_cases=case_links(note['related_case_ids'])) for note in rows]


def save_context(client, item, points, pdf):
    related = candidate_cases(item['title'], points, item['source_url'], item.get('body_text'), pdf)
    if not points and not related:
        return
    context_key = json.dumps([points, related], ensure_ascii=False)
    note_id = str(uuid.uuid5(uuid.UUID(item['id']), context_key))
    row = dict(workspace_id=client.workspace, intake_id=item['id'], id=note_id,
               points=points, related_case_ids=related)
    try:
        client.request('/rest/v1/kdp_intake_notes', method='POST', body=row)
    except SyncError as error:
        if str(error) != 'http_409':
            raise


def store_entry(client, payload, *, pdf=None, link_only=False):
    kind = 'pdf' if pdf is not None else 'text'
    title = field(payload, 'title', 180)
    company = field(payload, 'company_id', 8)
    if company not in ('all', 'ckd', 'hold', 'kb'):
        raise ValueError('invalid_intake')
    points = field(payload, 'review_points', 2000, optional=True)
    rights = '참고 주소' if link_only else field(payload, 'rights_basis', 500)
    url = source_url(field(payload, 'source_url', 1024, optional=not link_only))
    body = url if link_only else payload.get('text') if kind == 'text' else None
    if kind == 'text' and (not isinstance(body, str) or not body.strip() or len(body) > 100000 or '\x00' in body):
        raise ValueError('invalid_intake')
    raw = body.encode() if body is not None else pdf
    if kind == 'pdf' and (not raw.startswith(b'%PDF-') or len(raw) > PDF_LIMIT):
        raise ValueError('invalid_intake_pdf')
    digest = hashlib.sha256(raw).hexdigest()
    key = json.dumps(['link' if link_only else kind, company, title, url, digest], ensure_ascii=False)
    entry_id = str(uuid.uuid5(uuid.UUID(client.workspace), key))
    row = dict(workspace_id=client.workspace, id=entry_id, kind=kind, title=title,
               company_id=company, source_url=url, rights_basis=rights,
               sha256=digest, byte_length=len(raw), body_text=body)
    if link_only:
        row['origin_format'] = 'link'
    db_path = '/rest/v1/kdp_intake_entries'
    try:
        client.request(db_path, method='POST', body=row)
    except SyncError as error:
        if str(error) != 'http_409':
            raise
    try:
        item = entry(client, entry_id, detail=True)
    except FileNotFoundError:
        raise SyncError('intake_pending_other_editor') from None
    if kind == 'text' or item['stored_at']:
        save_context(client, item, points, pdf)
        return item['id']
    upload = '/storage/v1/object/' + BUCKET + '/' + item['object_path']
    try:
        checked_pdf(client, item)
    except SyncError as error:
        if str(error) not in ('http_400', 'http_404'):
            raise
        try:
            client.request(upload, method='POST', body=raw, content_type='application/pdf')
        except SyncError as upload_error:
            # An identical retry/concurrent request may have already created the object.
            if str(upload_error) not in ('http_400', 'http_409'):
                raise
        checked_pdf(client, item)
    filters = urlencode({'workspace_id': 'eq.' + client.workspace, 'id': 'eq.' + entry_id,
                         'stored_at': 'is.null'})
    client.request(db_path + '?' + filters, method='PATCH', body={'stored_at': 'now'})
    if not entry(client, entry_id)['stored_at']:
        raise SyncError('intake_not_committed')
    save_context(client, item, points, pdf)
    return entry_id
