-- Run only against the approved development database. Fixtures roll back.
-- This verifies SQL privileges/RLS and the registration gate, not Storage HTTP.
begin;
set local statement_timeout='25s';
do $check$
declare
  ws uuid := gen_random_uuid(); other uuid := gen_random_uuid();
  editor uuid := gen_random_uuid(); reader uuid := gen_random_uuid(); outsider uuid := gen_random_uuid();
  doc uuid := gen_random_uuid(); pdf uuid := gen_random_uuid(); link uuid := gen_random_uuid();
  note uuid := gen_random_uuid();
  digest text := repeat('a',64);
begin
  insert into auth.users(id) values(editor),(reader),(outsider);
  insert into public.kdp_workspaces(id,slug,name) values (ws,ws::text,'Intake test'),(other,other::text,'Other test');
  insert into public.kdp_workspace_members(workspace_id,user_id,member_role)
    values(ws,editor,'editor'),(ws,reader,'viewer'),(other,outsider,'owner');
  execute 'set local role anon';
  if has_table_privilege(current_user,'public.kdp_intake_entries','SELECT') or
     has_table_privilege(current_user,'public.kdp_reference_sites','SELECT') or
     has_table_privilege(current_user,'public.kdp_intake_notes','SELECT') then
    raise exception 'anonymous intake read allowed';
  end if;
  execute 'reset role';
  perform set_config('request.jwt.claim.sub',editor::text,true);
  execute 'set local role authenticated';
  insert into public.kdp_reference_sites(workspace_id,url,title,category) values(ws,'https://example.org/','Fixture','filing');
  insert into public.kdp_intake_entries(workspace_id,id,kind,title,company_id,rights_basis,sha256,byte_length,body_text)
    values(ws,doc,'text','Fixture','ckd','fixture only',digest,4,'test');
  insert into public.kdp_intake_entries(workspace_id,id,kind,title,company_id,rights_basis,sha256,byte_length)
    values(ws,pdf,'pdf','Fixture PDF','all','fixture only',digest,10);
  insert into public.kdp_intake_entries(workspace_id,id,kind,title,company_id,rights_basis,sha256,byte_length,body_text,source_url,origin_format)
    values(ws,link,'text','Link','all','link only',digest,20,'https://example.org/','https://example.org/','link');
  insert into public.kdp_intake_notes(workspace_id,intake_id,id,points,related_case_ids)
    values(ws,link,note,'배당기준일 확인',array['dividend']);
  if (select count(*) from public.kdp_intake_entries where workspace_id=ws)<>3 then raise exception 'editor data missing'; end if;
  if not exists(select 1 from public.kdp_intake_notes where id=note and created_by=editor) then
    raise exception 'editor review points missing';
  end if;
  begin
    update public.kdp_intake_notes set points='changed' where id=note;
    raise exception 'review points were editable';
  exception when insufficient_privilege then null; end;
  begin
    update public.kdp_intake_entries set stored_at=now() where id=pdf;
    raise exception 'unverified PDF accepted';
  exception when raise_exception then
    if sqlerrm<>'intake_pdf_object_required' then raise; end if;
  end;
  begin
    update public.kdp_intake_entries set sha256=repeat('b',64) where id=pdf;
    raise exception 'immutable hash accepted';
  exception when insufficient_privilege then null; end;
  perform set_config('request.jwt.claim.sub',reader::text,true);
  if exists(select 1 from public.kdp_intake_entries where id=pdf) or
     not exists(select 1 from public.kdp_intake_entries where id=doc) or
     not exists(select 1 from public.kdp_reference_sites where workspace_id=ws) or
     not exists(select 1 from public.kdp_intake_notes where id=note) then
    raise exception 'reader visibility is invalid';
  end if;
  begin
    insert into public.kdp_reference_sites(workspace_id,url,title,category) values(ws,'https://example.net/','Forbidden','filing');
    raise exception 'reader wrote a site';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.kdp_intake_notes(workspace_id,intake_id,id,points) values(ws,link,gen_random_uuid(),'reader');
    raise exception 'reader wrote a note';
  exception when insufficient_privilege then null; end;
  perform set_config('request.jwt.claim.sub',outsider::text,true);
  if exists(select 1 from public.kdp_intake_entries where workspace_id=ws) or
     exists(select 1 from public.kdp_reference_sites where workspace_id=ws) or
     exists(select 1 from public.kdp_intake_notes where workspace_id=ws) then
    raise exception 'other workspace read intake';
  end if;
  begin
    insert into public.kdp_reference_sites(workspace_id,url,title,category) values(ws,'https://example.net/','Forbidden','filing');
    raise exception 'other workspace wrote a site';
  exception when insufficient_privilege then null; end;
end
$check$;
rollback;
select 'pass' as intake_permissions, false as storage_http_verified;
