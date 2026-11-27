begin;
alter table public.kdp_intake_entries add column origin_format text not null default 'document';
alter table public.kdp_intake_entries add constraint kdp_intake_origin_format
  check (origin_format='document' or (origin_format='link' and kind='text'
         and source_url is not null and source_url=body_text));
grant insert (origin_format) on public.kdp_intake_entries to authenticated;

create table public.kdp_intake_notes (
  workspace_id uuid not null,
  intake_id uuid not null,
  id uuid not null,
  points text not null default '' check (length(points) <= 2000),
  related_case_ids text[] not null default '{}' check (cardinality(related_case_ids) <= 5),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  primary key (workspace_id,id),
  foreign key (workspace_id,intake_id) references public.kdp_intake_entries(workspace_id,id),
  check (length(btrim(points)) > 0 or cardinality(related_case_ids) > 0)
);
create index kdp_intake_notes_entry_idx on public.kdp_intake_notes(workspace_id,intake_id,created_at desc);
create index kdp_intake_notes_actor_idx on public.kdp_intake_notes(created_by);
alter table public.kdp_intake_notes enable row level security;
revoke all on public.kdp_intake_notes from public,anon,authenticated;
grant select on public.kdp_intake_notes to authenticated;
grant insert (workspace_id,intake_id,id,points,related_case_ids) on public.kdp_intake_notes to authenticated;
create policy kdp_intake_notes_read on public.kdp_intake_notes for select to authenticated
  using (kdp_private.can_read(workspace_id) and exists (
    select 1 from public.kdp_intake_entries e
    where e.workspace_id=kdp_intake_notes.workspace_id and e.id=kdp_intake_notes.intake_id
  ));
create policy kdp_intake_notes_insert on public.kdp_intake_notes for insert to authenticated
  with check (kdp_private.can_write(workspace_id) and created_by=(select auth.uid()) and exists (
    select 1 from public.kdp_intake_entries e
    where e.workspace_id=kdp_intake_notes.workspace_id and e.id=kdp_intake_notes.intake_id
  ));
commit;
