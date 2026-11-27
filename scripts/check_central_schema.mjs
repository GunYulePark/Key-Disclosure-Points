// Local PostgreSQL/WASM check. Supabase Auth/Storage tables below are fixtures;
// this does NOT verify hosted Auth, Storage HTTP, advisors, or two physical PCs.
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
const dependencyRoot = resolve(process.env.KDP_SQL_CHECK_DEPS || '.local/task01/sql-check');
const require = createRequire(resolve(dependencyRoot, 'package.json'));
const { PGlite } = require('@electric-sql/pglite');
const db = new PGlite();
let passed = 0;
async function test(name, fn) {
  await fn(); passed++; console.log(`PASS ${name}`);
}
async function rejected(sql, pattern) {
  await assert.rejects(db.exec(sql), pattern);
}
async function asUser(user, fn) {
  await db.exec(`set role authenticated; set request.jwt.claim.sub = '${user}'`);
  try { await fn(); } finally { await db.exec('reset role'); }
}
const ws='11111111-1111-4111-8111-111111111111';
const other='22222222-2222-4222-8222-222222222222';
const user='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const viewer='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const outsider='cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const source='33333333-3333-4333-8333-333333333333';
const doc='44444444-4444-4444-8444-444444444444';
const version='55555555-5555-4555-8555-555555555555';
const file='66666666-6666-4666-8666-666666666666';
const hash='a'.repeat(64);
const object=`${ws}/originals/${doc}/${version}/${hash}.pdf`;
const migrationRoot = resolve('supabase/migrations');
try {
  await db.exec(`
    create role anon; create role authenticated; create role service_role bypassrls;
    create schema auth; create schema storage;
    create table auth.users(id uuid primary key);
    create function auth.uid() returns uuid language sql stable as
      $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
    grant usage on schema auth,storage to anon,authenticated,service_role;
    grant execute on function auth.uid() to anon,authenticated,service_role;
    create table storage.objects(bucket_id text,name text,metadata jsonb,primary key(bucket_id,name));
    alter table storage.objects enable row level security;
    grant select,insert,update,delete on storage.objects to anon,authenticated,service_role;
  `);
  await test('all migrations execute in PostgreSQL', async()=>{
    for (const filename of (await readdir(migrationRoot)).filter(x=>x.endsWith('.sql')).sort()) {
      await db.exec(await readFile(resolve(migrationRoot,filename),'utf8'));
    }
  });
  await test('complete file identity FK has a covering index',async()=>{
    const r=await db.query("select indexdef from pg_indexes where schemaname='public' and indexname='kdp_files_version_identity_idx'");
    assert.equal(r.rows.length,1);
    assert.match(r.rows[0].indexdef,/\(workspace_id, document_version_id, sha256, byte_length\)/);
  });
  await test('hosted SQL verification script executes and rolls back fixtures',async()=>{
    await db.exec(await readFile(resolve('scripts/check_hosted_central.sql'),'utf8'));
    assert.equal((await db.query('select count(*)::int n from auth.users')).rows[0].n,0);
    assert.equal((await db.query('select count(*)::int n from public.kdp_workspaces')).rows[0].n,0);
  });
  await test('intake access and missing object checks roll back fixtures', async()=>{
    await db.exec(await readFile(resolve('scripts/check_hosted_intake.sql'),'utf8'));
    assert.equal((await db.query('select count(*)::int n from public.kdp_intake_entries')).rows[0].n,0);
    assert.equal((await db.query('select count(*)::int n from public.kdp_reference_sites')).rows[0].n,0);
  });
  await db.exec(`
    insert into auth.users values ('${user}'),('${viewer}'),('${outsider}');
    insert into public.kdp_workspaces(id,slug,name) values ('${ws}','test-a','Fixture A'),('${other}','test-b','Fixture B');
    insert into public.kdp_workspace_members(workspace_id,user_id,member_role) values
      ('${ws}','${user}','editor'),('${ws}','${viewer}','viewer'),('${other}','${outsider}','owner');
    insert into public.kdp_sources(workspace_id,id,source_url,rights_status,transfer_approved,approved_by,approved_at)
      values ('${ws}','${source}','https://dart.fss.or.kr/test','permitted',true,'local-fixture',now());
    insert into public.kdp_documents(workspace_id,id,source_id,legacy_identity,title,document_type)
      values ('${ws}','${doc}','${source}','fixture','Fixture only','regulation');
    insert into public.kdp_document_versions(workspace_id,id,document_id,sha256,byte_length,version_label)
      values ('${ws}','${version}','${doc}','${hash}',100,'fixture');
    insert into public.kdp_document_files(workspace_id,id,document_version_id,bucket_id,object_path,sha256,byte_length,mime_type)
      values ('${ws}','${file}','${version}','kdp-dev-originals','${object}','${hash}',100,'application/pdf');
  `);
  await test('intake PDF only opens to members after an immutable object is registered', async()=>{
    const intake='77777777-7777-4777-8777-777777777777';
    const candidate=`${ws}/intake/${intake}.pdf`;
    await db.exec('begin');
    try {
      await asUser(user, async()=>{
        await db.exec(`insert into public.kdp_intake_entries(workspace_id,id,kind,title,company_id,rights_basis,sha256,byte_length)
          values ('${ws}','${intake}','pdf','Fixture','all','fixture','${hash}',100)`);
        await db.exec(`insert into storage.objects(bucket_id,name,metadata)
          values ('kdp-dev-originals','${candidate}','{"size":100}')`);
        await db.exec(`update public.kdp_intake_entries set stored_at=now() where id='${intake}'`);
      });
      await asUser(viewer, async()=>{
        const result = await db.query(`select name from storage.objects where name='${candidate}'`);
        assert.deepEqual(result.rows,[{name:candidate}]);
      });
      await asUser(outsider, async()=>assert.equal((await db.query(`select name from storage.objects where name='${candidate}'`)).rows.length,0));
    } finally {await db.exec('rollback');}
  });
  await test('all twelve development tables enable RLS', async()=>{
    const r=await db.query("select count(*)::int n from pg_tables where schemaname='public' and tablename like 'kdp_%' and rowsecurity");
    assert.equal(r.rows[0].n,12);
  });
  await test('member sees only own workspace',async()=>asUser(user,async()=>{
    const r=await db.query('select id from public.kdp_workspaces'); assert.deepEqual(r.rows,[{id:ws}]);
    assert.equal((await db.query('select * from public.kdp_workspace_members')).rows.length,1);
  }));
  await test('other workspace cannot read metadata',async()=>asUser(outsider,async()=>{
    assert.equal((await db.query('select * from public.kdp_document_files')).rows.length,0);
  }));
  await test('anon cannot select core tables',async()=>{
    await db.exec('set role anon');
    try { await rejected('select * from public.kdp_documents',/permission denied/); }
    finally { await db.exec('reset role'); }
  });
  await test('membership cannot be self-promoted',async()=>asUser(viewer,async()=>{
    await rejected("update public.kdp_workspace_members set member_role='owner'",/permission denied/);
  }));
  await test('client cannot approve transfer or metadata',async()=>asUser(user,async()=>{
    await rejected('update public.kdp_sources set transfer_approved=true',/permission denied/);
  }));
  await test('cross-workspace foreign key rejected',async()=>rejected(`
    insert into public.kdp_documents(workspace_id,id,source_id,legacy_identity,title,document_type)
    values('${other}','${doc}','${source}','cross','bad','bad')`,/foreign key/));
  await test('file hash/length must match parent version',async()=>rejected(`
    insert into public.kdp_document_files(workspace_id,id,document_version_id,bucket_id,object_path,sha256,byte_length,mime_type)
    values('${ws}','${source}','${version}','kdp-dev-originals','${ws}/originals/wrong','${hash}',101,'application/pdf')`,/foreign key/));
  await test('original path identity is immutable',async()=>rejected(
    "update public.kdp_document_files set object_path=object_path||'x'",/immutable_original_identity/));
  await test('version hash is immutable',async()=>rejected(
    `update public.kdp_document_versions set sha256='${'b'.repeat(64)}',revision=revision+1`,/immutable_version_identity/));
  await test('ready blocked before bytes and evidence verified',async()=>rejected(
    "update public.kdp_document_versions set processing_status='ready',revision=revision+1",/ready_requires/));
  await test('stale revision updates zero rows',async()=>{
    assert.equal((await db.query(`update public.kdp_documents set title='changed',revision=1 where workspace_id='${ws}' and id='${doc}' and revision=0 returning id`)).rows.length,1);
    assert.equal((await db.query(`update public.kdp_documents set title='stale',revision=1 where workspace_id='${ws}' and id='${doc}' and revision=0 returning id`)).rows.length,0);
  });
  await test('revision increment is required',async()=>rejected(
    "update public.kdp_documents set title='blind'",/revision_must_increment/));
  await test('viewer cannot upload staged original',async()=>asUser(viewer,async()=>{
    await rejected(`insert into storage.objects values ('kdp-dev-originals','${object}')`,/row-level security/);
  }));
  await test('editor can insert approved pre-registered path',async()=>asUser(user,async()=>{
    await db.exec(`insert into storage.objects values ('kdp-dev-originals','${object}')`);
    assert.equal((await db.query('select * from storage.objects')).rows.length,0);
  }));
  await test('unregistered storage path denied',async()=>asUser(user,async()=>{
    await rejected(`insert into storage.objects values ('kdp-dev-originals','${ws}/unexpected.pdf')`,/row-level security/);
  }));
  await test('unapproved source upload denied',async()=>{
    await db.exec('update public.kdp_sources set transfer_approved=false');
    try { await asUser(user,()=>rejected(`insert into storage.objects values ('kdp-dev-originals','${object}')`,/row-level security/)); }
    finally { await db.exec('update public.kdp_sources set transfer_approved=true'); }
  });
  await db.exec(`update public.kdp_document_files set verification_status='verified',verified_at=now()`);
  await test('member can read verified storage original',async()=>asUser(viewer,async()=>{
    assert.equal((await db.query('select * from storage.objects')).rows.length,1);
  }));
  await test('other workspace cannot read original',async()=>asUser(outsider,async()=>{
    assert.equal((await db.query('select * from storage.objects')).rows.length,0);
  }));
  await test('revoked transfer approval blocks storage read',async()=>{
    await db.exec('update public.kdp_sources set transfer_approved=false');
    try { await asUser(user,async()=>assert.equal((await db.query('select * from storage.objects')).rows.length,0)); }
    finally { await db.exec('update public.kdp_sources set transfer_approved=true'); }
  });
  await test('authenticated overwrite/delete denied',async()=>asUser(user,async()=>{
    assert.equal((await db.query("update storage.objects set name='replacement' returning name")).rows.length,0);
    assert.equal((await db.query('delete from storage.objects returning name')).rows.length,0);
    await rejected(`insert into storage.objects values ('kdp-dev-originals','${object}')`,/row-level security/);
  }));
  await test('unverified anchor still blocks ready',async()=>{
    await db.exec(`insert into public.kdp_evidence_spans(workspace_id,id,document_version_id,legacy_evidence_id,kind,exact_text,normalized_text_start)
      values('${ws}','${source}','${version}','fixture-anchor','text','fixture',0)`);
    await rejected("update public.kdp_document_versions set parser_version='fixture',processing_status='ready',revision=revision+1",/ready_requires/);
  });
  await test('verified original/evidence allows ready',async()=>{
    await db.exec(`update public.kdp_evidence_spans set verification_status='text_verified';
      update public.kdp_document_versions set parser_version='fixture',processing_status='ready',revision=revision+1`);
    assert.equal((await db.query('select processing_status from public.kdp_document_versions')).rows[0].processing_status,'ready');
  });
  const locationColumns = '(workspace_id,document_version_id,legacy_evidence_id,extractor_version,sha256,byte_length,location)';
  const location = '{"kind":"text","normalized_start":0,"normalized_end":7}';
  const insertLocation = (digest,payload) => `insert into public.kdp_evidence_locations ${locationColumns}
    values ('${ws}','${version}','fixture-anchor','kdp-locator-v1','${digest}',100,'${payload}')`;
  await test('stored location requires the exact original identity and known locator schema',async()=>{
    await rejected(insertLocation('b'.repeat(64),location),/foreign key/);
    await rejected(insertLocation(hash,'{"kind":"text","normalized_start":0,"normalized_end":7,"extra":true}'),/check constraint/);
    await db.exec(insertLocation(hash,location));
  });
  await test('location visible to viewer but not writable, anonymous or cross-workspace',async()=>{
    await asUser(viewer,async()=>{
      assert.equal((await db.query('select * from public.kdp_evidence_locations')).rows.length,1);
      await rejected('update public.kdp_evidence_locations set location=location',/permission denied/);
    });
    await asUser(outsider,async()=>assert.equal((await db.query('select * from public.kdp_evidence_locations')).rows.length,0));
    await db.exec('set role anon');
    try {await rejected('select * from public.kdp_evidence_locations',/permission denied/);}
    finally {await db.exec('reset role');}
  });
  await test('revoking source approval hides stored location without deleting it',async()=>{
    await db.exec('update public.kdp_sources set transfer_approved=false');
    try {await asUser(viewer,async()=>assert.equal((await db.query('select * from public.kdp_evidence_locations')).rows.length,0));}
    finally {await db.exec('update public.kdp_sources set transfer_approved=true');}
    assert.equal((await db.query('select * from public.kdp_evidence_locations')).rows.length,1);
  });
  console.log(JSON.stringify({passed,engine:'PGlite PostgreSQL fixture',hosted_supabase_verified:false}));
} finally { await db.close(); }
