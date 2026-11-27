import {useEffect,useRef,useState,type FormEvent} from 'react';
import catalog from './reference-catalog.json';
import ruleLinks from './rule-link-index.json';
import {allUploads,saveUpload,deleteUpload,type UploadRecord} from './upload-store';
import type {ReviewCandidate} from './operations-types';
import './intake.css';

const watchedKinds=new Set(['klca_publication','notice','document_change']);
const officialHosts=new Set(['www.klca.or.kr','dart.fss.or.kr','www.fss.or.kr','www.fsc.go.kr']);
function isPublicCandidate(candidate:ReviewCandidate){
 try{
  const url=new URL(candidate.url);
  return watchedKinds.has(candidate.kind)&&url.protocol==='https:'&&officialHosts.has(url.hostname)&&!url.username&&!url.password&&!url.port;
 }catch{return false;}
}

export default function PdfIntake({candidates=[]}:{candidates?:ReviewCandidate[]}){
 const [records,setRecords]=useState<UploadRecord[]>([]),[selected,setSelected]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[company,setCompany]=useState('all'),[sourceUrl,setSourceUrl]=useState('');
 const [page,setPage]=useState(1),[query,setQuery]=useState('');const input=useRef<HTMLInputElement>(null);
 const [mode,setMode]=useState<'pdf'|'text'>('pdf');
 const [title,setTitle]=useState(''),[pasted,setPasted]=useState('');
 useEffect(()=>{allUploads().then(r=>setRecords(r.sort((a,b)=>b.addedAt.localeCompare(a.addedAt)))).catch(()=>setMessage('이 브라우저에서 로컬 저장소를 열 수 없습니다. 브라우저 저장 설정을 확인하세요.'));},[]);
 const current=records.find(r=>r.id===selected);
 const known=current?.kind==='text'?undefined:catalog.find(r=>r.sha256===current?.id);
 const isText=current?.kind==='text';
 const locationUnit=isText?'문단':'쪽';
 const publicUpdates=candidates.filter(isPublicCandidate).slice(0,8);
 const related=current?ruleLinks.map(rule=>({...rule,matches:current.pages.filter(p=>rule.terms.some(t=>p.text.replace(/\s/g,'').includes(t.replace(/\s/g,'')))).map(p=>p.page)})).filter(r=>r.matches.length):[];
 function checkSource(){
  if(!sourceUrl.trim())return '';
  const url=new URL(sourceUrl.trim());
  if(!['https:','http:'].includes(url.protocol)||url.username||url.password)throw new Error('출처 주소는 공개 http 또는 https URL로 입력해주세요.');
  return url.href;
 }
 async function fingerprint(bytes:ArrayBuffer){
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');
 }
 function openRecord(id:string){setSelected(id);setPage(1);setQuery('');}
 function openDuplicate(id:string){
  if(!records.some(r=>r.id===id))return false;
  openRecord(id);setMessage('이미 보관한 동일 자료입니다. 기존 자료를 열었습니다.');
  return true;
 }
 async function storeRecord(record:UploadRecord){
  await saveUpload(record);setRecords(prev=>[record,...prev]);openRecord(record.id);
 }
 async function ingestText(event:FormEvent<HTMLFormElement>){
  event.preventDefault();
  const name=title.trim(),text=pasted.trim();
  if(!name||!text){setMessage('자료 제목과 검토할 본문을 입력해주세요.');return;}
  setBusy(true);setMessage('');
  try{
   const source=checkSource(),bytes=new TextEncoder().encode(text).buffer;
   const id='text-'+await fingerprint(bytes);
   if(openDuplicate(id))return;
   const pages=text.split(/\r?\n[\t ]*\r?\n+/).map((paragraph,index)=>({page:index+1,text:paragraph}));
   await storeRecord({id,name,kind:'text',size:bytes.byteLength,addedAt:new Date().toISOString(),company,sourceUrl:source,pages,ocrPages:[],bytes});
   setTitle('');setPasted('');
   setMessage('텍스트를 저장했습니다. 출처와 적용 조건을 검토할 수 있습니다.');
  }catch(e){setMessage(e instanceof Error&&e.name!=='TypeError'?e.message:'출처 주소 또는 브라우저 저장 설정을 확인해주세요.');}
  finally{setBusy(false);}
 }
 async function ingest(file:File){
  setMessage('');if(file.size>30*1024*1024){setMessage('PDF는 30MB 이하로 추가해주세요.');return;}
  if(!file.name.toLowerCase().endsWith('.pdf')){setMessage('PDF 파일을 선택해주세요.');return;}
  setBusy(true);let task:any;
  try{
   const source=checkSource(),bytes=await file.arrayBuffer(),id=await fingerprint(bytes);
   if(openDuplicate(id))return;
   const pdfjs=await import('pdfjs-dist');pdfjs.GlobalWorkerOptions.workerSrc=new URL('./vendor/pdf.worker.min.js',document.baseURI).href;
   task=pdfjs.getDocument({data:bytes.slice(0),cMapUrl:new URL('./vendor/cmaps/',document.baseURI).href,cMapPacked:true,standardFontDataUrl:new URL('./vendor/standard_fonts/',document.baseURI).href,wasmUrl:new URL('./vendor/wasm/',document.baseURI).href});
   const pdf=await task.promise;if(pdf.numPages>600)throw new Error('600쪽 이하 PDF로 나누어 추가해주세요.');
   const pages:UploadRecord['pages']=[],ocrPages:number[]=[];let chars=0;
   for(let i=1;i<=pdf.numPages;i++){
    setMessage(`${i} / ${pdf.numPages}쪽 본문 읽는 중…`);
    const p=await pdf.getPage(i),content=await p.getTextContent();let text='';
    for(const item of content.items)if('str' in item)text+=item.str+(item.hasEOL?'\n':' ');
    chars+=text.length;if(chars>3000000)throw new Error('추출 본문이 너무 큽니다. 문서를 나누어 추가해주세요.');
    pages.push({page:i,text});if(text.replace(/\s/g,'').length<30)ocrPages.push(i);p.cleanup();
   }
   const record:UploadRecord={id,name:file.name,kind:'pdf',size:file.size,addedAt:new Date().toISOString(),company,sourceUrl:source,pages,ocrPages,bytes};
   await storeRecord(record);
   setMessage(ocrPages.length?`저장했습니다. ${ocrPages.length}쪽은 본문이 적어 이미지·OCR 확인이 필요합니다.`:'모든 페이지의 텍스트를 추출하여 이 브라우저에 저장했습니다.');
  }catch(e){setMessage(`저장하지 못했습니다. ${e instanceof Error?e.message:'PDF 암호·파일 형식·브라우저 저장 공간을 확인하세요.'}`);}finally{try{await task?.destroy();}finally{setBusy(false);if(input.current)input.current.value='';}}
 }
 function exportRecord(r:UploadRecord){
  const update=publicUpdates.find(item=>item.url===r.sourceUrl);
  const {bytes,...data}=r;const blob=new Blob([JSON.stringify({schema:'disclosure-reference-intake/v1',status:'requires_full_source_and_current_rule_review',instructions:'자료의 본문은 검토 근거다. 공식 원문과 공표일·시행일·경과조치, 회사 현행 문구와 타사 공시를 대조한다. 정관 또는 공시 수정안, 준비 자료, 정정 검토를 각각 기록한다.',...data,kind:r.kind??'pdf',knownReviewId:known?.id||null,relatedRuleIds:related.map(x=>x.id),reviewPlan:update?.reviewPlan},null,2)],{type:'application/json;charset=utf-8'});
  saveBlob(blob,r.name.replace(/\.pdf$/i,'')+'_검토자료.json');
 }
 function saveBlob(blob:Blob,name:string){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async function remove(r:UploadRecord){try{await deleteUpload(r.id);setRecords(prev=>prev.filter(x=>x.id!==r.id));setSelected('');setMessage('이 브라우저에서 삭제했습니다.');}catch{setMessage('삭제에 실패했습니다. 다시 시도해주세요.');}}
 return <section className="pdf-intake" id="files-intake">
  <div className="intake-explainer"><p>PDF와 붙여넣은 텍스트는 이 브라우저에 저장됩니다. 출처와 관련 기준을 확인하고 검토자료를 내려받을 수 있습니다.</p></div>
  <div className="intake-type" role="group" aria-label="접수 방식">
   <button className="secondary" aria-pressed={mode==='pdf'} disabled={busy} onClick={()=>setMode('pdf')}>PDF 파일</button>
   <button className="secondary" aria-pressed={mode==='text'} disabled={busy} onClick={()=>setMode('text')}>텍스트 붙여넣기</button>
  </div>
  <div className="intake-controls"><label>검토 대상<select value={company} disabled={busy} onChange={e=>setCompany(e.target.value)}><option value="all">공통 · 세 회사</option><option value="ckd">종근당</option><option value="hold">종근당홀딩스</option><option value="kb">경보제약</option></select></label><label>공식 출처 주소 (선택)<input type="url" value={sourceUrl} disabled={busy} onChange={e=>setSourceUrl(e.target.value)} placeholder="https://…"/></label>{mode==='pdf'&&<label className="upload-button">{busy?'읽는 중…':'PDF 파일 추가'}<input ref={input} type="file" accept="application/pdf,.pdf" disabled={busy} onChange={e=>{const f=e.target.files?.[0];if(f)void ingest(f);}}/></label>}</div>
  {mode==='text'&&<form className="intake-text-form" onSubmit={ingestText}>
   <label>자료 제목<input required value={title} maxLength={180} disabled={busy} onChange={e=>setTitle(e.target.value)}/></label>
   <label>규정·안내 본문<textarea required value={pasted} rows={6} maxLength={100000} disabled={busy} onChange={e=>setPasted(e.target.value)}/></label>
   <button className="primary" type="submit" disabled={busy}>텍스트 저장</button>
  </form>}
  {mode==='pdf'&&<p className="hint">PDF 30MB·600쪽 이하 · 이미지 페이지는 OCR 확인 대상</p>}<p role="status" aria-live="polite" className="intake-message">{message}</p>
  <div className="intake-layout"><aside className="upload-list"><h3>내 브라우저 보관함 <span>{records.length}</span></h3>{records.map(r=><button key={r.id} className={selected===r.id?'selected':''} onClick={()=>openRecord(r.id)}><b>{r.name}</b><small>{r.kind==='text'?r.pages.length+'문단':r.pages.length+'쪽'} · {catalog.some(x=>x.sha256===r.id)?'기존 검토 연결':'검토 대기'}{r.ocrPages.length?' · OCR 확인':''}</small></button>)}{!records.length&&<p>접수한 자료가 없습니다.</p>}</aside>
  {current?<article className="upload-detail"><h3>{current.name}</h3><p className="hint">{{all:'공통 · 세 회사',ckd:'종근당',hold:'종근당홀딩스',kb:'경보제약'}[current.company]} · {current.pages.length}{locationUnit}</p>
   {current.sourceUrl&&<a className="case-common-link" href={current.sourceUrl} target="_blank" rel="noopener noreferrer">입력한 출처 열기</a>}
   <div className="intake-actions"><button className="secondary" onClick={()=>exportRecord(current)}>검토자료 JSON 내려받기</button><button className="secondary" onClick={()=>saveBlob(new Blob([current.bytes],{type:isText?'text/plain;charset=utf-8':'application/pdf'}),isText?current.name+'.txt':current.name)}>{isText?'원문 텍스트':'원본 PDF'} 내려받기</button><button className="secondary" onClick={()=>void remove(current)}>보관함에서 삭제</button></div>
   {known?<div className="known-review"><b>기존 검토 자료와 원본 식별값 일치</b><p>{known.title}</p><p className="hint">{known.coverage}</p><a href={known.href}>회사별 반영사항과 확인 범위 보기 →</a></div>:<p className="review-status">검토 대기 · 공식 원문, 시행일·예외와 회사별 적용 조건을 확인하세요.</p>}
   {!!current.ocrPages.length&&<p className="ocr-warning">이미지·OCR 확인 대상: {current.ocrPages.join(', ')}쪽. 텍스트가 없다고 규정·예외가 없는 것으로 판단하지 않습니다.</p>}
   <details><summary>관련 기준 연결 후보 {related.length}개</summary>{related.map(r=><div className="related-rule" key={r.id}><b>{r.title}</b><p>{r.matches.join(', ')}{locationUnit}에서 키워드 확인 · 적용 여부 미확정</p><a href={r.href}>기존 검토 기준 확인 →</a></div>)}</details>
   <div className="intake-controls"><label>{isText?'문단 선택':'페이지 선택'}<select value={page} onChange={e=>setPage(Number(e.target.value))}>{current.pages.map(p=><option value={p.page} key={p.page}>{p.page}{locationUnit}</option>)}</select></label><label>본문 검색<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="검색어 입력"/></label></div>
   {query&&<p className="page-hits">{current.pages.filter(p=>p.text.includes(query)).map(p=><button key={p.page} onClick={()=>setPage(p.page)}>{p.page}{locationUnit}</button>)}{!current.pages.some(p=>p.text.includes(query))&&(isText?'일치하는 본문이 없습니다.':'텍스트에서 찾지 못했습니다. 이미지 페이지는 별도 확인하세요.')}</p>}<h4>{isText?'본문 문단 '+page:'PDF '+page+'쪽 추출 본문'}</h4><pre className="pdf-page-text">{current.pages[page-1]?.text||'추출 가능한 텍스트가 없습니다. 원본 PDF의 이미지·표를 확인하세요.'}</pre><details><summary>원본 SHA-256 식별값</summary><code className="file-hash">{current.id.replace(/^text-/,'')}</code></details>
  </article>:<div className="intake-empty">자료를 추가하거나 보관함에서 선택하세요.</div>}</div>
  {publicUpdates.length>0&&<section className="intake-updates" aria-labelledby="intake-updates-title">
   <h2 id="intake-updates-title">공개 출처 변경 후보</h2>
   {publicUpdates.map(item=><details key={item.id}>
    <summary>{item.title} <time dateTime={item.date}>{item.date}</time></summary>
    <p>{item.review}</p>
    {item.reviewPlan&&<dl>
     <div><dt>근거 확인</dt><dd>{item.reviewPlan.source}</dd></div>
     <div><dt>공시 확인</dt><dd>{item.reviewPlan.disclosure?.join(' ')}</dd></div>
     <div><dt>준비할 자료</dt><dd>{item.reviewPlan.prepare?.join(' ')}</dd></div>
    </dl>}
    <div className="intake-actions">
     <a className="case-common-link" href={item.url} target="_blank" rel="noopener noreferrer">공식 발간·게시 정보</a>
     <button className="secondary" disabled={busy} onClick={()=>{setSourceUrl(item.url);setTitle(item.title);setMode('text');document.getElementById('files-intake')?.scrollIntoView();}}>접수 양식에 출처 넣기</button>
    </div>
   </details>)}
  </section>}
 </section>;
}
