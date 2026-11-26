"""Prepare backed-up, approved evidence locations for the development database."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from central_ingest import approved_batch, read_json
from central_sync import SyncError, identity, safe_target
from evidence_view import evidence_view


EXTRACTOR_VERSION = 'kdp-locator-v1'
LOCATION_FIELDS = {
    'html': ('section_id', 'table_id', 'row_id', 'cell_id'),
    'pdf': ('page_index', 'page_label', 'page_count', 'intrinsic_rotation',
            'width', 'height', 'boxes', 'coordinate_system'),
    'text': (),
}


def canonical_location(view):
    kind = view['kind']
    if kind == 'image':
        # Manual observations have no computed coordinates.
        return {'kind': 'image', 'manual': True}
    location = {key: view[key] for key in ('kind', 'normalized_start', 'normalized_end', *LOCATION_FIELDS[kind])}
    if kind == 'pdf':
        # Stable values across geometry conversions and JSON round trips.
        location['width'] = round(location['width'], 3)
        location['height'] = round(location['height'], 3)
        location['boxes'] = [[round(value, 3) for value in box] for box in location['boxes']]
    return location


def location_records(batch, cache):
    result = []
    for source, _, workspace in batch:
        path = safe_target(cache, source['cache_key'])
        if path.stat().st_size != source['bytes']:
            raise ValueError('original_hash_or_size_mismatch')
        raw = path.read_bytes()
        version = identity(source, workspace)['version_id']
        for anchor in source['anchors']:
            result.append({
                'workspace_id': workspace, 'document_version_id': version,
                'legacy_evidence_id': anchor['id'], 'extractor_version': EXTRACTOR_VERSION,
                'sha256': source['sha256'], 'byte_length': source['bytes'],
                'source_url': source['url'], 'anchor_kind': anchor['kind'],
                'anchor_text': anchor.get('text'), 'anchor_start': anchor.get('start'),
                'page_index': anchor['pdf_page'] - 1 if 'pdf_page' in anchor else None,
                'location_note': anchor.get('location'),
                'location': canonical_location(evidence_view(source, anchor, raw)),
            })
    return result


def dollar_quote(value, name):
    while (tag := f'${name}$') in value:
        name += '_'
    return tag + value + tag


def seed_sql(records):
    data = dollar_quote(json.dumps(records, ensure_ascii=False, allow_nan=False, separators=(',', ':')), 'locations')
    body = f"""
declare
  a jsonb;
  ws uuid;
  version uuid;
begin
  for a in select value from jsonb_array_elements({data}::jsonb) loop
    ws := (a->>'workspace_id')::uuid;
    version := (a->>'document_version_id')::uuid;
    if not exists (
      select 1 from public.kdp_evidence_spans e
      join public.kdp_document_versions v on (v.workspace_id,v.id)=(e.workspace_id,e.document_version_id)
      join public.kdp_documents d on (d.workspace_id,d.id)=(v.workspace_id,v.document_id)
      join public.kdp_sources s on (s.workspace_id,s.id)=(d.workspace_id,d.source_id)
      join public.kdp_document_files f on (f.workspace_id,f.document_version_id)=(v.workspace_id,v.id)
      where e.workspace_id=ws and e.document_version_id=version and e.legacy_evidence_id=a->>'legacy_evidence_id'
        and e.kind=a->>'anchor_kind' and e.exact_text is not distinct from a->>'anchor_text'
        and e.normalized_text_start is not distinct from (a->>'anchor_start')::int
        and e.page_index is not distinct from (a->>'page_index')::int
        and e.location_note is not distinct from a->>'location_note'
        and e.verification_status=case when e.kind='text' then 'text_verified' else 'manually_verified' end
        and v.processing_status='ready'
        and s.source_url=a->>'source_url' and s.transfer_approved and s.rights_status='permitted'
        and f.verification_status='verified' and f.bucket_id='kdp-dev-originals'
        and f.sha256=a->>'sha256' and f.byte_length=(a->>'byte_length')::bigint
    ) then raise exception 'location_requires_verified_approved_evidence'; end if;
    insert into public.kdp_evidence_locations
      (workspace_id,document_version_id,legacy_evidence_id,extractor_version,sha256,byte_length,location)
    values (ws,version,a->>'legacy_evidence_id',a->>'extractor_version',a->>'sha256',
            (a->>'byte_length')::bigint,a->'location')
    on conflict (workspace_id,document_version_id,legacy_evidence_id,extractor_version) do nothing;
    if not exists (
      select 1 from public.kdp_evidence_locations l
      where l.workspace_id=ws and l.document_version_id=version
        and l.legacy_evidence_id=a->>'legacy_evidence_id' and l.extractor_version=a->>'extractor_version'
        and l.sha256=a->>'sha256' and l.byte_length=(a->>'byte_length')::bigint and l.location=a->'location'
    ) then raise exception 'location_extractor_conflict'; end if;
  end loop;
end;
"""
    return 'do ' + dollar_quote(body, 'backfill_locations') + ';\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pack', 'target', 'approval', 'files', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(Path('.local').resolve()):
        parser.error('write the seed to an ignored .local/ path')
    pack, approval, target = map(read_json, (args.pack, args.approval, args.target))
    batch = list(approved_batch(pack, approval, target, os.environ))
    records = location_records(batch, args.files)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as output:
        output.write(seed_sql(records))
    print(json.dumps({'sources': len(batch), 'locations': len(records), 'cloud_writes': 0}))


if __name__ == '__main__':
    try:
        main()
    except (SyncError, ValueError, KeyError, OSError) as error:
        print('evidence_location_seed_failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
