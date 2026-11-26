-- Dedicated KDP development project only, after the core migration.
-- All fixture users and metadata roll back. No Auth HTTP sessions are created.
-- Storage bytes/API behavior and file verification are NOT tested here.
begin;
set local lock_timeout = '5s';
set local statement_timeout = '30s';
do $check$
declare
  ws uuid := gen_random_uuid(); other_ws uuid := gen_random_uuid();
  actor uuid := gen_random_uuid(); outsider uuid := gen_random_uuid();
  src uuid := gen_random_uuid(); doc uuid := gen_random_uuid();
  ver uuid := gen_random_uuid(); file_id uuid := gen_random_uuid();
  digest text := repeat('a',64); n integer;
begin
  if (select count(*) from pg_tables where schemaname='public'
      and tablename like 'kdp_%' and rowsecurity) <> 9 then
    raise exception 'check 1: core RLS';
  end if;
  if (select count(*) from pg_policies where schemaname='storage'
      and tablename='objects' and policyname like 'kdp_%'
      and cmd in ('SELECT','INSERT')) <> 2
    or exists(select 1 from pg_policies where schemaname='storage'
      and tablename='objects' and cmd in ('ALL','UPDATE','DELETE')) then
    raise exception 'check 2: storage policies';
  end if;
  -- Transaction-only identities satisfy the real auth.users FK; no sign-in.
  insert into auth.users(id) values(actor),(outsider);
  insert into public.kdp_workspaces(id,slug,name) values
    (ws,ws::text,'SQL rollback fixture'),(other_ws,other_ws::text,'SQL outsider fixture');
  insert into public.kdp_workspace_members(workspace_id,user_id,member_role)
    values(ws,actor,'viewer'),(other_ws,outsider,'owner');
  insert into public.kdp_sources(workspace_id,id,source_url)
    values(ws,src,'https://example.com/kdp-sql-fixture');
  insert into public.kdp_documents(workspace_id,id,source_id,legacy_identity,title,document_type)
    values(ws,doc,src,'sql-fixture','SQL fixture only','fixture');
  insert into public.kdp_document_versions(workspace_id,id,document_id,sha256,byte_length,version_label)
    values(ws,ver,doc,digest,100,'fixture');
  insert into public.kdp_document_files(workspace_id,id,document_version_id,bucket_id,object_path,sha256,byte_length,mime_type)
    values(ws,file_id,ver,'kdp-dev-originals',ws::text||'/originals/fixture.pdf',digest,100,'application/pdf');

  execute 'set local role anon';
  begin
    perform 1 from public.kdp_documents;
    raise exception 'check 3: anon metadata was accessible';
  exception when insufficient_privilege then null; end;
  execute 'reset role';
  perform set_config('request.jwt.claim.sub',actor::text,true);
  execute 'set local role authenticated';
  if (select count(*) from public.kdp_workspaces) <> 1
      or (select count(*) from public.kdp_workspace_members) <> 1 then
    raise exception 'check 4: workspace isolation';
  end if;
  begin
    update public.kdp_workspace_members set member_role='owner' where workspace_id=ws;
    raise exception 'check 5: self promotion permitted';
  exception when insufficient_privilege then null; end;
  begin
    update public.kdp_sources set transfer_approved=true where workspace_id=ws;
    raise exception 'check 6: client approval permitted';
  exception when insufficient_privilege then null; end;
  perform set_config('request.jwt.claim.sub',outsider::text,true);
  if exists(select 1 from public.kdp_document_files where workspace_id=ws) then
    raise exception 'check 7: outsider saw file manifest';
  end if;
  execute 'reset role';

  begin
    insert into public.kdp_documents(workspace_id,id,source_id,legacy_identity,title,document_type)
      values(other_ws,gen_random_uuid(),src,'cross','Cross workspace','fixture');
    raise exception 'check 8: cross workspace FK accepted';
  exception when foreign_key_violation then null; end;
  begin
    insert into public.kdp_document_files(workspace_id,id,document_version_id,bucket_id,object_path,sha256,byte_length,mime_type)
      values(ws,gen_random_uuid(),ver,'kdp-dev-originals',ws::text||'/originals/mismatch.pdf',digest,101,'application/pdf');
    raise exception 'check 9: file length mismatch accepted';
  exception when foreign_key_violation then null; end;
  begin
    update public.kdp_document_versions set sha256=repeat('b',64),revision=revision+1 where workspace_id=ws;
    raise exception 'check 10: immutable version changed';
  exception when raise_exception then
    if sqlerrm <> 'immutable_version_identity' then raise; end if;
  end;
  begin
    update public.kdp_document_files set object_path=object_path||'x' where workspace_id=ws;
    raise exception 'check 11: immutable file changed';
  exception when raise_exception then
    if sqlerrm <> 'immutable_original_identity' then raise; end if;
  end;
  begin
    update public.kdp_document_versions set processing_status='ready',revision=revision+1 where workspace_id=ws;
    raise exception 'check 12: unverified version became ready';
  exception when raise_exception then
    if sqlerrm <> 'ready_requires_verified_original_and_evidence' then raise; end if;
  end;
  update public.kdp_documents set revision=1 where workspace_id=ws and id=doc and revision=0;
  get diagnostics n = row_count;
  if n <> 1 then raise exception 'check 13: first revision write failed'; end if;
  update public.kdp_documents set revision=1 where workspace_id=ws and id=doc and revision=0;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'check 13: stale revision write accepted'; end if;
  begin
    update public.kdp_documents set title='Blind write' where workspace_id=ws;
    raise exception 'check 14: revision not required';
  exception when raise_exception then
    if sqlerrm <> 'revision_must_increment' then raise; end if;
  end;
  -- Fixture metadata only: no claim of downloading or verifying real bytes.
  update public.kdp_sources set rights_status='permitted',transfer_approved=true,
    approved_by='rollback-fixture',approved_at=now() where workspace_id=ws;
  update public.kdp_document_files set verification_status='verified',verified_at=now() where workspace_id=ws;
  insert into public.kdp_evidence_spans(workspace_id,id,document_version_id,legacy_evidence_id,kind,exact_text,normalized_text_start,verification_status)
    values(ws,gen_random_uuid(),ver,'fixture','text','fixture',0,'text_verified');
  update public.kdp_document_versions set parser_version='fixture',processing_status='ready',revision=revision+1 where workspace_id=ws;
  if not exists(select 1 from public.kdp_document_versions where workspace_id=ws and processing_status='ready') then
    raise exception 'check 15: verified fixture ready transition failed';
  end if;
end
$check$;
rollback;
select 15 as passed, 'hosted SQL with rolled-back fixtures' as scope,
  false as auth_http_verified, false as storage_http_verified;
