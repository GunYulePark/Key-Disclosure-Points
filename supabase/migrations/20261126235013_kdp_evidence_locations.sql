-- Derived locations are immutable by extractor version and bound to exact source bytes.
begin;

create table public.kdp_evidence_locations (
  workspace_id uuid not null,
  document_version_id uuid not null,
  legacy_evidence_id text not null,
  extractor_version text not null check (extractor_version ~ '^kdp-locator-v[1-9][0-9]*$'),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  byte_length bigint not null check (byte_length > 0),
  location jsonb not null,
  created_at timestamptz not null default now(),
  primary key (workspace_id,document_version_id,legacy_evidence_id,extractor_version),
  foreign key (workspace_id,document_version_id,legacy_evidence_id)
    references public.kdp_evidence_spans(workspace_id,document_version_id,legacy_evidence_id),
  foreign key (workspace_id,document_version_id,sha256,byte_length)
    references public.kdp_document_versions(workspace_id,id,sha256,byte_length),
  check (jsonb_typeof(location) = 'object' and pg_column_size(location) <= 16384
    and location ? 'kind' and case location->>'kind'
      when 'html' then location ?& array['normalized_start','normalized_end','section_id','table_id','row_id','cell_id']
        and jsonb_typeof(location->'section_id') = 'string'
        and (location - array['kind','normalized_start','normalized_end','section_id','table_id','row_id','cell_id']) = '{}'::jsonb
      when 'pdf' then location ?& array['normalized_start','normalized_end','page_index','page_label','page_count','intrinsic_rotation',
                                      'width','height','boxes','coordinate_system']
        and jsonb_typeof(location->'boxes') = 'array' and location->'boxes' <> '[]'::jsonb
        and location->>'coordinate_system' = 'cropbox-top-left-unrotated-points'
        and (location - array['kind','normalized_start','normalized_end','page_index','page_label','page_count','intrinsic_rotation',
                              'width','height','boxes','coordinate_system']) = '{}'::jsonb
      when 'text' then location ?& array['normalized_start','normalized_end']
        and (location - array['kind','normalized_start','normalized_end']) = '{}'::jsonb
      when 'image' then location = '{"kind":"image","manual":true}'::jsonb
      else false
    end
    and case when location->>'kind' in ('pdf','html','text') then
      jsonb_typeof(location->'normalized_start') = 'number' and jsonb_typeof(location->'normalized_end') = 'number'
      and (location->'normalized_start')::numeric >= 0 and (location->'normalized_end')::numeric > (location->'normalized_start')::numeric
    else true end)
);
-- Primary key covers the citation FK and workspace + version lookups.
create index kdp_locations_version_identity_idx
  on public.kdp_evidence_locations(workspace_id,document_version_id,sha256,byte_length);

alter table public.kdp_evidence_locations enable row level security;
revoke all on public.kdp_evidence_locations from public, anon, authenticated, service_role;
grant select on public.kdp_evidence_locations to authenticated;

create policy kdp_locations_read_approved on public.kdp_evidence_locations
for select to authenticated using (
  kdp_private.can_read(workspace_id)
  and exists (
    select 1
    from public.kdp_evidence_spans e
    join public.kdp_document_versions v on (v.workspace_id,v.id) = (e.workspace_id,e.document_version_id)
    join public.kdp_documents d on (d.workspace_id,d.id) = (v.workspace_id,v.document_id)
    join public.kdp_sources s on (s.workspace_id,s.id) = (d.workspace_id,d.source_id)
    where (e.workspace_id,e.document_version_id,e.legacy_evidence_id) =
          (kdp_evidence_locations.workspace_id,kdp_evidence_locations.document_version_id,kdp_evidence_locations.legacy_evidence_id)
      and e.verification_status in ('text_verified','manually_verified')
      and v.processing_status = 'ready' and s.transfer_approved and s.rights_status = 'permitted'
      and exists (
        select 1 from public.kdp_document_files f
        where (f.workspace_id,f.document_version_id,f.sha256,f.byte_length) =
              (kdp_evidence_locations.workspace_id,kdp_evidence_locations.document_version_id,
               kdp_evidence_locations.sha256,kdp_evidence_locations.byte_length)
          and f.verification_status = 'verified' and f.bucket_id = 'kdp-dev-originals'
      )
  )
);

commit;
