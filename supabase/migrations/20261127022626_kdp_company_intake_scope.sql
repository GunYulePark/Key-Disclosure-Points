begin;

alter table public.kdp_workspace_members add column intake_company_id text
  check (intake_company_id is null or (intake_company_id in ('ckd','hold','kb') and member_role <> 'owner'));

create function kdp_private.intake_scope_allows(ws uuid, company text) returns boolean
  language sql stable security invoker set search_path = '' as $$
  select exists (
    select 1 from public.kdp_workspace_members m
    where m.workspace_id = ws and m.user_id = (select auth.uid())
      and (m.intake_company_id is null or company = 'all' or m.intake_company_id = company)
  )
$$;
revoke all on function kdp_private.intake_scope_allows(uuid,text) from public,anon,authenticated;
grant execute on function kdp_private.intake_scope_allows(uuid,text) to authenticated,service_role;

-- Existing editor/viewer and PDF registration rules still apply in addition to scope.
-- The PDF objects and review notes also require a visible parent entry.
create policy kdp_intake_company_scope on public.kdp_intake_entries as restrictive
  for all to authenticated
  using (kdp_private.intake_scope_allows(workspace_id,company_id))
  with check (kdp_private.intake_scope_allows(workspace_id,company_id));

-- The reference directory is shared. Company-specific links belong in intake.
create policy kdp_reference_site_workspace_maintainer on public.kdp_reference_sites as restrictive
  for insert to authenticated with check (kdp_private.intake_scope_allows(workspace_id,null));

-- The evidence catalogue predates company classification. Leave it with its
-- existing workspace-level accounts until each original has an approved scope.
do $catalogue$
declare t text;
begin
  foreach t in array array['kdp_sources','kdp_documents','kdp_document_versions',
    'kdp_document_files','kdp_evidence_spans','kdp_evidence_locations',
    'kdp_legacy_id_map','kdp_ingestion_jobs'] loop
    execute format('create policy kdp_workspace_wide_catalogue on public.%I as restrictive
      for select to authenticated using (kdp_private.intake_scope_allows(workspace_id,null))',t);
  end loop;
end
$catalogue$;

commit;
