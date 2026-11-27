"""Prepare an approved original batch and finalize it from independent downloads.

Storage transport and SQL execution use the development project's authorized
admin session. This command prepares local files and SQL only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from case_pack import pack_fingerprint, validate_pack, verify_source
from central_contract import NAMESPACE
from central_sync import BUCKET, MIMES, SyncError, identity, safe_target, target_config
from research_retention import allow_research_original


def stable_id(kind, key):
    return str(uuid.uuid5(NAMESPACE, kind + '\n' + key))


def approved_batch(pack, approval, target, env, *, stage_originals=True):
    _, workspace = target_config(target, env)
    validate_pack(pack)
    if (approval['project_ref'] != target['project_ref']
            or approval['workspace_id'] != workspace
            or approval['pack_fingerprint'] != pack_fingerprint(pack)
            or approval.get('transfer_approved') is not True
            or not str(approval.get('approved_by', '')).strip()):
        raise SyncError('explicit_batch_approval_required')
    allowed = approval['sources']
    sources = {source['id']: source for source in pack['sources']}
    if not allowed or not set(allowed) <= sources.keys():
        raise SyncError('approved_sources_missing_or_unknown')
    for source_id, permission in allowed.items():
        source = sources[source_id]
        rights = urlsplit(permission['rights_url'])
        if (permission['sha256'] != source['sha256']
                or rights.scheme != 'https' or not rights.hostname
                or rights.username is not None or rights.password is not None
                or not permission['publisher'].strip()
                or not permission['document_type'].strip()):
            raise SyncError('source_rights_or_identity_invalid')
        if stage_originals and not allow_research_original(source, permission):
            raise SyncError('research_original_excerpt_by_default')
        if source['bytes'] > 10 * 1024 * 1024:
            raise SyncError('source_exceeds_bucket_limit')
        yield source, permission, workspace


def records(batch, approved_by):
    result = []
    for source, rights, workspace in batch:
        item = identity(source, workspace)
        version = item['version_id']
        result.append({
            **item, 'workspace_id': workspace, 'bucket_id': BUCKET,
            'file_id': stable_id('file', item['object_path']),
            'source_id': stable_id('source', source['url']),
            'job_id': stable_id('job', version),
            'legacy_id': source['id'], 'source_url': source['url'],
            'publisher': rights['publisher'], 'document_type': rights['document_type'],
            'rights_url': rights['rights_url'], 'approved_by': approved_by,
            'title': source['title'], 'version_label': source['version_label'],
            'sha256': source['sha256'], 'bytes': source['bytes'],
            'mime_type': MIMES[source['format']],
            'anchors': [{
                'id': stable_id('evidence', version + '\n' + anchor['id']),
                'legacy_id': anchor['id'], 'kind': anchor['kind'],
                'text': anchor.get('text'), 'start': anchor.get('start'),
                'page_index': anchor['pdf_page'] - 1 if 'pdf_page' in anchor else None,
                'location': anchor.get('location'),
            } for anchor in source['anchors']],
        })
    return result


STAGE = """
insert into public.kdp_sources(workspace_id,id,source_url,publisher,legal_nature,
  rights_status,transfer_approved,approved_by,approved_at)
values(ws,src,d->>'source_url',d->>'publisher',d->>'document_type',
  'permitted',true,d->>'approved_by',now())
on conflict do nothing;
if not exists (select from public.kdp_sources where workspace_id=ws and id=src
  and source_url=d->>'source_url' and rights_status='permitted' and transfer_approved) then
  raise exception 'source conflict or approval revoked';
end if;
insert into public.kdp_documents(workspace_id,id,source_id,legacy_identity,title,document_type)
values(ws,doc,src,d->>'legacy_id',d->>'title',d->>'document_type') on conflict do nothing;
if not exists (select from public.kdp_documents where workspace_id=ws and id=doc
  and source_id=src and legacy_identity=d->>'legacy_id') then
  raise exception 'document identity conflict';
end if;
insert into public.kdp_document_versions(workspace_id,id,document_id,sha256,byte_length,version_label)
values(ws,v,doc,d->>'sha256',(d->>'bytes')::bigint,d->>'version_label') on conflict do nothing;
if not exists (select from public.kdp_document_versions where workspace_id=ws and id=v
  and document_id=doc and sha256=d->>'sha256' and byte_length=(d->>'bytes')::bigint) then
  raise exception 'version identity conflict';
end if;
insert into public.kdp_document_files(workspace_id,id,document_version_id,bucket_id,
  object_path,sha256,byte_length,mime_type)
values(ws,f,v,d->>'bucket_id',d->>'object_path',d->>'sha256',(d->>'bytes')::bigint,d->>'mime_type')
on conflict do nothing;
insert into public.kdp_ingestion_jobs(workspace_id,id,idempotency_key,document_version_id)
values(ws,j,'original:'||v::text,v) on conflict do nothing;
"""

IDENTITY_CHECK = """
if not exists (select from public.kdp_document_files where workspace_id=ws and id=f
  and document_version_id=v and bucket_id=d->>'bucket_id' and object_path=d->>'object_path'
  and sha256=d->>'sha256' and byte_length=(d->>'bytes')::bigint and mime_type=d->>'mime_type')
or not exists (select from public.kdp_ingestion_jobs where workspace_id=ws and id=j
  and idempotency_key='original:'||v::text and document_version_id=v) then
  raise exception 'file or job identity conflict';
end if;
"""

FINISH = """
if not exists (select from public.kdp_sources where workspace_id=ws and id=src
  and source_url=d->>'source_url' and rights_status='permitted' and transfer_approved) then
  raise exception 'source approval no longer current';
end if;
if not exists (
  select from storage.objects o join storage.buckets b on b.id=o.bucket_id
  where not b.public and o.bucket_id=d->>'bucket_id' and o.name=d->>'object_path'
    and o.metadata->>'size'=d->>'bytes'
) then
  raise exception 'private storage object missing or size changed';
end if;
for a in select value from jsonb_array_elements(d->'anchors') loop
  insert into public.kdp_evidence_spans(workspace_id,id,document_version_id,legacy_evidence_id,
    kind,exact_text,normalized_text_start,page_index,location_note,verification_status)
  values(ws,(a->>'id')::uuid,v,a->>'legacy_id',a->>'kind',a->>'text',(a->>'start')::integer,
    (a->>'page_index')::integer,a->>'location',
    case when a->>'kind'='text' then 'text_verified' else 'unverified' end)
  on conflict do nothing;
  if not exists (select from public.kdp_evidence_spans where workspace_id=ws and id=(a->>'id')::uuid
    and document_version_id=v and legacy_evidence_id=a->>'legacy_id' and kind=a->>'kind'
    and exact_text is not distinct from a->>'text'
    and normalized_text_start is not distinct from (a->>'start')::integer
    and page_index is not distinct from (a->>'page_index')::integer
    and location_note is not distinct from a->>'location') then
    raise exception 'evidence identity conflict';
  end if;
end loop;
insert into public.kdp_legacy_id_map(workspace_id,legacy_system,legacy_id,document_version_id)
values(ws,'priority-case-pack',d->>'legacy_id',v) on conflict do nothing;
update public.kdp_document_files set verification_status='verified',verified_at=now()
where workspace_id=ws and id=f and verification_status<>'verified';
next_state := case when exists (select from public.kdp_evidence_spans where workspace_id=ws
  and document_version_id=v and verification_status='unverified') then 'hash_verified' else 'ready' end;
update public.kdp_document_versions set parser_version='case-pack-v1',processing_status=next_state,revision=revision+1
where workspace_id=ws and id=v and processing_status not in ('ready',next_state);
update public.kdp_ingestion_jobs set stage=next_state,revision=revision+1,updated_at=now()
where workspace_id=ws and id=j and stage not in ('ready',next_state);
"""


def migration_sql(items, *, finish=False):
    payload = json.dumps(items, ensure_ascii=False, separators=(',', ':'))
    tag = '$payload$'
    while tag in payload:
        tag = tag[:-1] + '_$'
    body = IDENTITY_CHECK + FINISH if finish else STAGE + IDENTITY_CHECK
    block = f"""
declare
  d jsonb; a jsonb; ws uuid; src uuid; doc uuid; v uuid; f uuid; j uuid; next_state text;
begin
  for d in select value from jsonb_array_elements({tag}{payload}{tag}::jsonb) loop
    ws := (d->>'workspace_id')::uuid;
    src := (d->>'source_id')::uuid; doc := (d->>'document_id')::uuid;
    v := (d->>'version_id')::uuid; f := (d->>'file_id')::uuid; j := (d->>'job_id')::uuid;
    {body}
  end loop;
end;
"""
    outer = '$ingest$'
    while outer in block:
        outer = outer[:-1] + '_$'
    return f'DO {outer}{block}{outer};\n'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage', 'finish'])
    parser.add_argument('--pack', required=True, type=Path)
    parser.add_argument('--target', required=True, type=Path)
    parser.add_argument('--approval', required=True, type=Path)
    parser.add_argument('--files', required=True, type=Path, help='Original cache or separate download folder')
    parser.add_argument('--out', required=True, type=Path, help='New directory under ignored .local/')
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(Path('.local').resolve()):
        raise SyncError('ignored_local_output_required')
    pack, approval, target = map(read_json, [args.pack, args.approval, args.target])
    batch = list(approved_batch(pack, approval, target, os.environ,
                                stage_originals=args.action == 'stage'))
    items = records(batch, approval['approved_by'])
    # Validate the complete batch before producing any upload or SQL artifact.
    for source, _, _ in batch:
        verify_source(source, safe_target(args.files, source['cache_key']).read_bytes())
    output.mkdir(parents=True)
    if args.action == 'stage':
        for (source, _, _), item in zip(batch, items):
            local = output / 'upload' / item['object_path']
            local.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe_target(args.files, source['cache_key']), local)
            verify_source(source, local.read_bytes())
    (output / 'batch.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / (args.action + '.sql')).write_text(
        migration_sql(items, finish=args.action == 'finish'), encoding='utf-8')
    print(json.dumps({'stage': args.action, 'files': len(items),
                      'bytes': sum(item['bytes'] for item in items), 'cloud_writes': 0}))


if __name__ == '__main__':
    try:
        main()
    except (SyncError, ValueError, KeyError, OSError) as exc:
        reason = str(exc) if isinstance(exc, SyncError) else type(exc).__name__
        print('central_ingest_failed: ' + reason, file=sys.stderr)
        raise SystemExit(1)
