-- TASK 01 core. Generated with Supabase CLI 3.3.0; NOT applied to hosted DB.
-- New, dedicated DEVELOPMENT project only. Bucket creation uses Storage API.
begin;
create schema if not exists kdp_private;
revoke all on schema kdp_private from public, anon, authenticated;
grant usage on schema kdp_private to authenticated, service_role;

create table public.kdp_workspaces (
  id uuid primary key, slug text not null unique, name text not null,
  revision bigint not null default 0 check (revision >= 0),
  created_at timestamptz not null default now()
);
create table public.kdp_workspace_members (
  workspace_id uuid not null references public.kdp_workspaces(id),
  user_id uuid not null references auth.users(id),
  member_role text not null check (member_role in ('owner','editor','viewer')),
  created_at timestamptz not null default now(),
  primary key (workspace_id,user_id)
);
create index kdp_member_user_idx on public.kdp_workspace_members(user_id,workspace_id);

-- Membership is provisioned by a trusted administrator, never user_metadata.
alter table public.kdp_workspace_members enable row level security;
create policy kdp_members_self_read on public.kdp_workspace_members
  for select to authenticated using (user_id = (select auth.uid()));
create function kdp_private.can_read(ws uuid) returns boolean
  language sql stable security invoker set search_path = '' as $$
  select exists (select 1 from public.kdp_workspace_members
    where workspace_id = ws and user_id = (select auth.uid()))
$$;
create function kdp_private.can_write(ws uuid) returns boolean
  language sql stable security invoker set search_path = '' as $$
  select exists (select 1 from public.kdp_workspace_members
    where workspace_id = ws and user_id = (select auth.uid())
      and member_role in ('owner','editor'))
$$;
revoke all on function kdp_private.can_read(uuid), kdp_private.can_write(uuid) from public;
grant execute on function kdp_private.can_read(uuid), kdp_private.can_write(uuid)
  to authenticated, service_role;

create table public.kdp_sources (
  workspace_id uuid not null references public.kdp_workspaces(id),
  id uuid not null, source_url text not null check (source_url like 'https://%'),
  publisher text, legal_nature text,
  rights_status text not null default 'unverified'
    check (rights_status in ('unverified','permitted','restricted')),
  transfer_approved boolean not null default false,
  approved_by text, approved_at timestamptz,
  primary key (workspace_id,id), unique (workspace_id,source_url),
  check (not transfer_approved or
    (rights_status = 'permitted' and approved_by is not null and approved_at is not null))
);
create table public.kdp_documents (
  workspace_id uuid not null, id uuid not null, source_id uuid not null,
  legacy_identity text not null, title text not null, document_type text not null,
  revision bigint not null default 0 check (revision >= 0),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  primary key (workspace_id,id), unique (workspace_id,source_id,legacy_identity),
  foreign key (workspace_id,source_id) references public.kdp_sources(workspace_id,id)
);
create table public.kdp_document_versions (
  workspace_id uuid not null, id uuid not null, document_id uuid not null,
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  byte_length bigint not null check (byte_length > 0), version_label text not null,
  receipt_no text, published_on date, effective_from date, effective_to date,
  collected_at timestamptz, parser_version text,
  processing_status text not null default 'staged'
    check (processing_status in ('staged','object_uploaded','hash_verified','parsed','ready','failed')),
  review_status text not null default 'unverified' check (review_status in ('unverified','reviewed')),
  revision bigint not null default 0 check (revision >= 0),
  primary key (workspace_id,id), unique (workspace_id,document_id,sha256),
  unique (workspace_id,id,sha256,byte_length),
  foreign key (workspace_id,document_id) references public.kdp_documents(workspace_id,id),
  check (effective_to is null or effective_from is null or effective_to >= effective_from)
);
create index kdp_versions_document_idx on public.kdp_document_versions(workspace_id,document_id);
create table public.kdp_document_files (
  workspace_id uuid not null, id uuid not null, document_version_id uuid not null,
  bucket_id text not null check (bucket_id = 'kdp-dev-originals'),
  object_path text not null, sha256 text not null,
  byte_length bigint not null check (byte_length > 0), mime_type text not null,
  verification_status text not null default 'staged' check (verification_status in ('staged','verified','failed')),
  verified_at timestamptz,
  primary key (workspace_id,id), unique (bucket_id,object_path),
  foreign key (workspace_id,document_version_id,sha256,byte_length)
    references public.kdp_document_versions(workspace_id,id,sha256,byte_length),
  check (object_path like workspace_id::text || '/originals/%'),
  check (object_path !~ '(^|/)\.\.?(/|$)' and object_path !~ '[%\\]'),
  check (verification_status <> 'verified' or verified_at is not null)
);
create index kdp_files_version_idx on public.kdp_document_files(workspace_id,document_version_id);
create table public.kdp_evidence_spans (
  workspace_id uuid not null, id uuid not null, document_version_id uuid not null,
  legacy_evidence_id text not null, kind text not null check (kind in ('text','visual')),
  exact_text text, normalized_text_start integer check (normalized_text_start >= 0),
  page_index integer check (page_index >= 0), location_note text,
  verification_status text not null default 'unverified'
    check (verification_status in ('unverified','text_verified','manually_verified')),
  primary key (workspace_id,id), unique (workspace_id,document_version_id,legacy_evidence_id),
  foreign key (workspace_id,document_version_id) references public.kdp_document_versions(workspace_id,id),
  check ((kind = 'text' and exact_text is not null and normalized_text_start is not null)
    or (kind = 'visual' and location_note is not null))
);
create table public.kdp_legacy_id_map (
  workspace_id uuid not null, legacy_system text not null, legacy_id text not null,
  document_version_id uuid not null,
  primary key (workspace_id,legacy_system,legacy_id,document_version_id),
  foreign key (workspace_id,document_version_id) references public.kdp_document_versions(workspace_id,id)
);
create index kdp_legacy_version_idx on public.kdp_legacy_id_map(workspace_id,document_version_id);
create table public.kdp_ingestion_jobs (
  workspace_id uuid not null references public.kdp_workspaces(id), id uuid not null,
  idempotency_key text not null, document_version_id uuid,
  stage text not null default 'staged'
    check (stage in ('staged','object_uploaded','hash_verified','parsed','ready','failed')),
  revision bigint not null default 0 check (revision >= 0),
  attempts integer not null default 0 check (attempts >= 0), error_code text,
  updated_at timestamptz not null default now(),
  primary key (workspace_id,id), unique (workspace_id,idempotency_key),
  foreign key (workspace_id,document_version_id) references public.kdp_document_versions(workspace_id,id)
);
create index kdp_jobs_version_idx on public.kdp_ingestion_jobs(workspace_id,document_version_id);
create index kdp_jobs_stage_idx on public.kdp_ingestion_jobs(workspace_id,stage,updated_at);

-- Only trusted server ingestion can mutate metadata/approvals. Client roles read
-- workspace-scoped data, and may INSERT a pre-registered approved storage path.
do $$
declare t text;
begin
  foreach t in array array['kdp_workspaces','kdp_sources','kdp_documents',
    'kdp_document_versions','kdp_document_files','kdp_evidence_spans',
    'kdp_legacy_id_map','kdp_ingestion_jobs'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('create policy %I on public.%I for select to authenticated using (kdp_private.can_read(%I))',
      t || '_read',t,case when t = 'kdp_workspaces' then 'id' else 'workspace_id' end);
  end loop;
  foreach t in array array['kdp_workspaces','kdp_workspace_members','kdp_sources','kdp_documents',
    'kdp_document_versions','kdp_document_files','kdp_evidence_spans','kdp_legacy_id_map','kdp_ingestion_jobs'] loop
    execute format('revoke all on public.%I from public, anon, authenticated',t);
    execute format('grant select on public.%I to authenticated',t);
    execute format('grant select,insert,update on public.%I to service_role',t);
  end loop;
end $$;

-- The object bytes and their identity are immutable even for service ingestion.
create function kdp_private.guard_file_identity() returns trigger
  language plpgsql security invoker set search_path = '' as $$
begin
  if row(new.workspace_id,new.id,new.document_version_id,new.bucket_id,new.object_path,new.sha256,new.byte_length,new.mime_type)
    is distinct from row(old.workspace_id,old.id,old.document_version_id,old.bucket_id,old.object_path,old.sha256,old.byte_length,old.mime_type) then
    raise exception 'immutable_original_identity';
  end if;
  return new;
end $$;
revoke all on function kdp_private.guard_file_identity() from public, anon, authenticated;
create trigger kdp_files_identity before update on public.kdp_document_files
  for each row execute function kdp_private.guard_file_identity();

create function kdp_private.guard_revision() returns trigger
  language plpgsql security invoker set search_path = '' as $$
begin
  if new.revision <> old.revision + 1 then raise exception 'revision_must_increment'; end if;
  return new;
end $$;
revoke all on function kdp_private.guard_revision() from public, anon, authenticated;
create trigger kdp_documents_revision before update on public.kdp_documents
  for each row execute function kdp_private.guard_revision();
create trigger kdp_versions_revision before update on public.kdp_document_versions
  for each row execute function kdp_private.guard_revision();
create trigger kdp_jobs_revision before update on public.kdp_ingestion_jobs
  for each row execute function kdp_private.guard_revision();

create function kdp_private.guard_version() returns trigger
  language plpgsql security invoker set search_path = '' as $$
begin
  if tg_op = 'UPDATE' and row(new.workspace_id,new.id,new.document_id,new.sha256,new.byte_length)
    is distinct from row(old.workspace_id,old.id,old.document_id,old.sha256,old.byte_length) then
    raise exception 'immutable_version_identity';
  end if;
  if new.processing_status = 'ready' and (
    new.parser_version is null or
    not exists (select 1 from public.kdp_document_files f
      join public.kdp_documents d on d.workspace_id=new.workspace_id and d.id=new.document_id
      join public.kdp_sources s on s.workspace_id=d.workspace_id and s.id=d.source_id
      where f.workspace_id=new.workspace_id and f.document_version_id=new.id
        and f.verification_status='verified' and s.transfer_approved) or
    not exists (select 1 from public.kdp_evidence_spans e
      where e.workspace_id=new.workspace_id and e.document_version_id=new.id) or
    exists (select 1 from public.kdp_evidence_spans e
      where e.workspace_id=new.workspace_id and e.document_version_id=new.id
        and e.verification_status='unverified')
  ) then raise exception 'ready_requires_verified_original_and_evidence'; end if;
  return new;
end $$;
revoke all on function kdp_private.guard_version() from public, anon, authenticated;
create trigger kdp_version_integrity before insert or update on public.kdp_document_versions
  for each row execute function kdp_private.guard_version();

-- No UPDATE/DELETE policy and no upsert: new bytes require a new immutable path.
create policy kdp_originals_read on storage.objects for select to authenticated
using (bucket_id = 'kdp-dev-originals' and exists (
  select 1 from public.kdp_document_files f
  join public.kdp_document_versions v on v.workspace_id=f.workspace_id and v.id=f.document_version_id
  join public.kdp_documents d on d.workspace_id=v.workspace_id and d.id=v.document_id
  join public.kdp_sources s on s.workspace_id=d.workspace_id and s.id=d.source_id
  where f.bucket_id = objects.bucket_id and f.object_path = objects.name
    and f.verification_status = 'verified' and s.transfer_approved
    and s.rights_status = 'permitted' and kdp_private.can_read(f.workspace_id)
));
create policy kdp_originals_insert on storage.objects for insert to authenticated
with check (bucket_id = 'kdp-dev-originals' and exists (
  select 1 from public.kdp_document_files f
  join public.kdp_document_versions v on v.workspace_id=f.workspace_id and v.id=f.document_version_id
  join public.kdp_documents d on d.workspace_id=v.workspace_id and d.id=v.document_id
  join public.kdp_sources s on s.workspace_id=d.workspace_id and s.id=d.source_id
  where f.bucket_id = objects.bucket_id and f.object_path = objects.name
    and f.verification_status = 'staged' and s.transfer_approved
    and kdp_private.can_write(f.workspace_id)
));
commit;
