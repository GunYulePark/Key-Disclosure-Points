"""TASK 00: local, read-only inventory. Never uploads or opens browser stores.

Detailed output stays in ignored .local/: filenames can themselves be private.
Source identity matched to an official URL does NOT grant redistribution rights.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

SKIP_DIRS={'.git','node_modules','docs','dist','vendor','.next','.vinext','.wrangler','.openai','.sites-runtime','__pycache__','.venv','tmp','.local','coverage'}
OFFICIAL={'dart.fss.or.kr','opendart.fss.or.kr','www.fss.or.kr','www.fsc.go.kr','kind.krx.co.kr','rule.krx.co.kr','www.law.go.kr'}
CATALOGS=['src/snapshot.json','public/data/q3-evidence-manifest.json','monitoring/state.json','monitoring/watch-documents.json']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def official(url):
 try:
  p=urlsplit(url);return p.scheme=='https' and p.hostname in OFFICIAL and not p.username and not p.password and p.port in (None,443)
 except (ValueError,TypeError):return False
def source_catalog(repo):
 hashes=defaultdict(list);refs=[]
 def walk(v):
  if isinstance(v,dict):
   url=v.get('url') or v.get('source_url');digest=v.get('sha256')
   if official(url):
    record={'url':url,'sha256':digest,'legacy_id':v.get('source_key') or v.get('key') or v.get('id'),'receipt_no':v.get('receipt_no')}
    refs.append(record)
    if isinstance(digest,str) and len(digest)==64:hashes[digest].append(record)
   for child in v.values():walk(child)
  elif isinstance(v,list):
   for child in v:walk(child)
 for name in CATALOGS:
  path=repo/name
  if path.exists():walk(json.loads(path.read_text(encoding='utf-8')))
 return hashes,refs
def inventory(workspace,repo):
 workspace=Path(workspace).resolve();repo=Path(repo).resolve()
 if not workspace.is_dir() or not repo.is_dir():raise ValueError('existing_workspace_and_repo_required')
 catalog,refs=source_catalog(repo);files=[];errors=[];skipped=Counter()
 for folder,dirs,names in os.walk(workspace,followlinks=False):
  kept=[]
  for d in dirs:
   p=Path(folder)/d
   if d in SKIP_DIRS or p.is_symlink() or getattr(p,'is_junction',lambda:False)():skipped[d]+=1
   else:kept.append(d)
  dirs[:]=kept
  for name in names:
   p=Path(folder)/name
   if p.is_symlink() or name.startswith('.env') or p.suffix.lower() in {'.pem','.key','.p12','.pfx'}:skipped['secret_or_link']+=1;continue
   relative=p.relative_to(workspace).as_posix()
   try:
    digest=sha(p);size=p.stat().st_size
   except OSError:errors.append({'path':relative,'error':'unreadable'});continue
   matches=catalog.get(digest,[])
   category='private_or_unclassified'
   if relative.startswith('sites/'):category='private_application_or_data'
   elif matches:category='official_public_origin_rights_pending'
   elif '/tests/' in '/'+relative or relative.startswith('tests/'):category='test_material'
   elif relative.startswith('data/'):category='legacy_material_review_required'
   elif p.suffix.lower() in {'.py','.ts','.tsx','.mjs','.css','.md','.toml','.yaml','.yml'}:category='source_or_documentation'
   files.append({'path':relative,'bytes':size,'sha256':digest,'suffix':p.suffix.lower(),'category':category,'official_matches':matches,'transfer_approved':False})
 groups=defaultdict(list)
 for f in files:groups[f['sha256']].append(f)
 available=set(groups)
 summary={'file_count':len(files),'bytes':sum(f['bytes'] for f in files),'unique_hashes':len(groups),'unique_bytes':sum(g[0]['bytes'] for g in groups.values()),'duplicate_copies':sum(len(g)-1 for g in groups.values()),'categories':{c:{'files':sum(f['category']==c for f in files),'bytes':sum(f['bytes'] for f in files if f['category']==c)} for c in sorted({f['category'] for f in files})},'official_references_with_hash':sum(bool(r['sha256']) for r in refs),'references_without_matching_local_hash':sum(bool(r['sha256']) and r['sha256'] not in available for r in refs),'unreadable_files':len(errors),'external_roots_scanned':False,'browser_indexeddb_inspected':False,'hosted_d1_inspected':False,'transfer_count':0,'skipped_directories':dict(skipped)}
 # Duplicate reference occurrences are not distinct documents; do not report
 # their count as missing documents or infer that a missing local hash is lost.
 return {'schema_version':1,'mode':'local_inventory_only','summary':summary,'files':files,'errors':errors}
def sample_plan(report):
 eligible=[f for f in report['files'] if f['category']=='official_public_origin_rights_pending']
 pdf=next((f for f in eligible if f['suffix']=='.pdf'),None)
 html=next((f for f in eligible if f['suffix'] in ('.html','.xml') and any('dart.fss.or.kr'==urlsplit(m['url']).hostname for m in f['official_matches'])),None)
 selected=[f for f in (pdf,html) if f]
 return {'mode':'dry_run_only','approval_required':True,'cloud_writes':0,'samples':[{'path':f['path'],'bytes':f['bytes'],'sha256':f['sha256'],'source':f['official_matches'][0],'transfer_approved':False} for f in selected],'total_bytes':sum(f['bytes'] for f in selected),'missing_types':[kind for kind,value in [('official_pdf',pdf),('dart_html_or_xml',html)] if value is None],'evaluation_records':'No approved evaluation records identified; synthetic fixtures must remain unverified.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,default=Path('.local/task00'));args=p.parse_args()
 output=args.output.resolve();repo=args.repo.resolve()
 if not output.is_relative_to(repo/'.local'):p.error('output must stay in the repository .local directory')
 report=inventory(args.workspace,repo);output.mkdir(parents=True,exist_ok=True)
 for name,value in [('inventory.json',report),('sample-dry-run.json',sample_plan(report))]:(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report['summary'],ensure_ascii=False))
if __name__=='__main__':main()
