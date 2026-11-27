begin;

create table public.kdp_intake_entries (
  workspace_id uuid not null references public.kdp_workspaces(id),
  id uuid not null,
  kind text not null check (kind in ('pdf','text')),
  title text not null check (length(btrim(title)) between 1 and 180),
  company_id text not null check (company_id in ('all','ckd','hold','kb')),
  source_url text check (length(source_url) <= 1024 and source_url ~ '^https://[a-zA-Z0-9.-]+([/?#][^[:space:][:cntrl:]]*)?$'),
  rights_basis text not null check (length(btrim(rights_basis)) between 1 and 500),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  byte_length integer not null check (byte_length between 1 and 10485760),
  body_text text,
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  stored_at timestamptz,
  object_path text generated always as (
    case when kind='pdf' then workspace_id::text || '/intake/' || id::text || '.pdf' end
  ) stored,
  primary key (workspace_id,id),
  check ((kind='pdf' and body_text is null) or
         (kind='text' and stored_at is null and body_text is not null
          and byte_length=octet_length(body_text) and length(body_text) between 1 and 100000))
);
create index kdp_intake_created_idx on public.kdp_intake_entries(workspace_id,created_at desc,id desc);
create index kdp_intake_actor_idx on public.kdp_intake_entries(created_by);
create unique index kdp_intake_path_idx on public.kdp_intake_entries(object_path) where object_path is not null;

create table public.kdp_reference_sites (
  workspace_id uuid not null references public.kdp_workspaces(id),
  url text not null check (length(url) <= 1024 and url ~ '^https://[a-zA-Z0-9.-]+([/?#][^[:space:][:cntrl:]]*)?$'),
  title text not null check (length(btrim(title)) between 1 and 160),
  category text not null check (category in ('filing','regulation','guidance','other')),
  note text not null default '' check (length(note) <= 500),
  created_by uuid default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  primary key (workspace_id,url)
);
create index kdp_reference_site_actor_idx on public.kdp_reference_sites(created_by);

alter table public.kdp_intake_entries enable row level security;
alter table public.kdp_reference_sites enable row level security;
revoke all on public.kdp_intake_entries, public.kdp_reference_sites from public, anon, authenticated;
grant select on public.kdp_intake_entries, public.kdp_reference_sites to authenticated;
grant insert (workspace_id,id,kind,title,company_id,source_url,rights_basis,sha256,byte_length,body_text)
  on public.kdp_intake_entries to authenticated;
grant update (stored_at) on public.kdp_intake_entries to authenticated;
grant insert (workspace_id,url,title,category,note) on public.kdp_reference_sites to authenticated;

create policy kdp_intake_read on public.kdp_intake_entries for select to authenticated
using (kdp_private.can_read(workspace_id) and
       (kind='text' or stored_at is not null or (created_by=(select auth.uid()) and kdp_private.can_write(workspace_id))));
create policy kdp_intake_insert on public.kdp_intake_entries for insert to authenticated
with check (kdp_private.can_write(workspace_id) and created_by=(select auth.uid()) and stored_at is null);
create policy kdp_intake_complete on public.kdp_intake_entries for update to authenticated
using (kdp_private.can_write(workspace_id) and created_by=(select auth.uid()) and kind='pdf' and stored_at is null)
with check (kdp_private.can_write(workspace_id) and created_by=(select auth.uid()) and stored_at is not null);
create policy kdp_reference_site_read on public.kdp_reference_sites for select to authenticated
using (kdp_private.can_read(workspace_id));
create policy kdp_reference_site_insert on public.kdp_reference_sites for insert to authenticated
with check (kdp_private.can_write(workspace_id) and created_by=(select auth.uid()));

-- Reuse the private bucket. Each intake PDF has one immutable object path.
create policy kdp_intake_object_insert on storage.objects for insert to authenticated
with check (bucket_id='kdp-dev-originals' and exists (
  select 1 from public.kdp_intake_entries e where e.object_path=objects.name
    and e.created_by=(select auth.uid()) and e.stored_at is null and kdp_private.can_write(e.workspace_id)
));
create policy kdp_intake_object_read on storage.objects for select to authenticated
using (bucket_id='kdp-dev-originals' and exists (
  select 1 from public.kdp_intake_entries e where e.object_path=objects.name
    and (e.stored_at is not null or e.created_by=(select auth.uid()))
));

-- Storage provides the object length. The intake server also re-reads and hashes the bytes.
create function kdp_private.check_intake_object() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
  if not exists (
    select 1 from storage.objects o
    where o.bucket_id='kdp-dev-originals' and o.name=old.object_path
      and o.metadata->>'size'=old.byte_length::text
  ) then raise exception 'intake_pdf_object_required'; end if;
  new.stored_at := now();
  return new;
end
$$;
revoke all on function kdp_private.check_intake_object() from public, anon, authenticated;
create trigger kdp_intake_object_check before update of stored_at on public.kdp_intake_entries
  for each row execute function kdp_private.check_intake_object();

commit;
