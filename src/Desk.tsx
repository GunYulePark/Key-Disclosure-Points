import { useEffect, useState } from "react";
import { ArrowUpRight, Search, LayoutDashboard, Library, BookOpen, Radio, ChevronRight, X, Download, Check, ShieldCheck, FileText, CircleAlert, RotateCw, Menu } from "lucide-react";
import data from "./snapshot.json";

type Finding = typeof data.findings[number];
const companies: Record<string,string> = { all: "전체 회사", ckd: "종근당", hold: "종근당홀딩스", kb: "경보제약" };
const ruleNotes: Record<string,string> = {
  FORMAT_CURRENT: "현행 편집본으로 보관합니다. 9월 개정의 공모펀드 항목을 세 회사의 필수 수정으로 일괄 적용하지 않습니다.",
  FORMAT_PREVIOUS: "종속회사 등 중복상장 관련 항목입니다. 해당 상장·신고 사건이 있을 때 적용조건을 검토합니다.",
  TREASURY_ATTACHMENT: "분기 자기주식보고서 첨부 생략 안내를 확인했습니다. 보유·처분계획서 변동 조건과 규정 원문 대조는 별도 점검합니다.",
  INDEPENDENT_DIRECTOR_LABEL: "작성 서식 버전과 독립이사 관련 용어를 점검합니다. 회사별 적용과 규정 원문 대조가 남아 있습니다.",
  BIO_GUIDANCE: "공식 안내와 HWP 파일을 확보했습니다. 업종별 본문 전수 검토와 회사별 적용 판단이 남아 있습니다.",
};
function download(name: string, value: unknown) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);
}
function FactView({ f }: { f: Finding }) {
  if(f.id === "CKD-OWNERSHIP") { const fact=f.facts as any;return <><div className="comparison"><div><small>직전 · 합산 보유</small><b>5,542,063주</b><span>40.15%</span></div><ChevronRight size={20}/><div><small>이번 · 합산 보유</small><b>5,542,063주</b><span>40.15% · 합계 불변</span></div></div><div className="table-scroll"><table><thead><tr><th>성명</th><th>변경 전</th><th>증감</th><th>변경 후</th></tr></thead><tbody>{fact.changes.map((c:any)=><tr key={c.name}><td>{c.name}</td><td>{c.before.toLocaleString()}</td><td className={c.delta<0?"red":"teal"}>{c.delta>0?"+":""}{c.delta.toLocaleString()}</td><td>{c.after.toLocaleString()}</td></tr>)}</tbody></table></div><p className="hint">거래일 2026.10.02 · 6월 말·9월 말 이후의 변동입니다.</p></>; }
  const pairs: Record<string,string[]> = {
    "HOLD-BASELINE":["2026.08.14 최초본","2026.10.12 정정본","자기주식보고서 미첨부","첨부 추가 · 상세표 변경"],
    "HOLD-TOTAL":["요약표 보통주","상세표 합계 행","249,303주","보통주 ‘-’ / 우선주 249,303주"],
    "HOLD-DATE":["권리행사 기간 · 추가 첨부","본문 계속보유 사유","2030.09.23","2030.09.30"],
    "HOLD-YEAR":["확인한 표기 ①","확인한 표기 ②","202년 10월","202년 12월"],
    "KB-FOLLOWUP":["2026.08.31","2026.09.30","항소 · 집행정지 신청 예정","집행정지 인용 · 본안 추적"],
    "HOLD-KB-FOLLOWUP":["2026.08.31","2026.09.30","항소 · 집행정지 신청 예정","집행정지 인용 · 본안 추적"],
  };
  const p=pairs[f.id];return <><div className="comparison"><div><small>{p[0]}</small><b>{p[2]}</b></div><ChevronRight size={20}/><div><small>{p[1]}</small><b>{p[3]}</b></div></div>{f.id.includes("FOLLOWUP")&&<p className="hint">종료 조건: 항소심 본안 판결 선고일 + 30일. 판결일·종료일은 미확인입니다.</p>}{f.id==="HOLD-BASELINE"&&<p className="hint">요약표 보통주 249,303주는 전후 동일합니다. 새로운 거래 발생으로 해석하지 않습니다.</p>}</>;
}

export default function Desk() {
  const [tab,setTab]=useState("issues"),[company,setCompany]=useState("all"),[q,setQ]=useState(""),[priority,setPriority]=useState("all"),[onlyCandidates,setOnlyCandidates]=useState(false),[from,setFrom]=useState(""),[to,setTo]=useState(""),[page,setPage]=useState(1);
  const [selected,setSelected]=useState<Finding|null>(null),[navOpen,setNavOpen]=useState(false);
  useEffect(()=>{setPage(1);},[company,q,from,to]);
  useEffect(()=>{
    if(!selected)return;
    const before=document.body.style.overflow,focused=document.activeElement as HTMLElement|null;
    document.body.style.overflow="hidden";
    const listener=(e:KeyboardEvent)=>{
      if(e.key==="Escape")setSelected(null);
      if(e.key==="Tab"){
        const items=Array.from(document.querySelectorAll<HTMLElement>('.detail-panel button, .detail-panel a, .detail-panel summary')).filter(el=>el.getClientRects().length);
        const first=items[0],last=items[items.length-1];
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
      }
    };
    document.addEventListener("keydown",listener);
    return()=>{document.body.style.overflow=before;document.removeEventListener("keydown",listener);focused?.focus();};
  },[selected]);
  function openDetail(f:Finding){setSelected(f);}
  function closeDetail(){setSelected(null);}
  const text=q.trim().toLowerCase();
  const issues=data.findings.filter(f=>(company==="all"||f.company_id===company)&&(priority==="all"||f.priority===priority)&&(!onlyCandidates||f.candidate)&&(!from||f.date>=from)&&(!to||f.date<=to)&&(!text||[f.title,f.instructions,f.id,companies[f.company_id],...f.evidence.map(e=>e.excerpt)].join(" ").toLowerCase().includes(text)));
  const filings=data.filings.filter(f=>(company==="all"||f.company_id===company)&&(!from||f.received_date>=from)&&(!to||f.received_date<=to)&&(!text||[f.title,f.receipt_no,f.filer,companies[f.company_id]].join(" ").toLowerCase().includes(text))).sort((a,b)=>b.received_date.localeCompare(a.received_date)||b.receipt_no.localeCompare(a.receipt_no));
  const scopeIssues=data.findings.filter(f=>company==="all"||f.company_id===company);
  const reset=()=>{setQ("");setPriority("all");setOnlyCandidates(false);setFrom("");setTo("");};
  const nav=(t:string)=>{setTab(t);reset();setNavOpen(false);};
  return <div className="app-shell">
    <aside className={`sidebar ${navOpen?"is-open":""}`}>
      <a className="brand" href="./" aria-label="공시 검토실 홈"><span className="brand-symbol"><FileText size={22}/></span><span>공시 검토실<small>DISCLOSURE DESK</small></span></a>
      <div className="workspace"><span className="workspace-icon">CK</span><div>CKD 공시 모니터링<small>공개 공시 자료실</small></div><ShieldCheck size={15}/></div>
      <p className="nav-label">WORKSPACE</p>
      <nav aria-label="주 메뉴">{[{id:"issues",label:"우선 점검",icon:LayoutDashboard,count:7},{id:"archive",label:"공시 보관함",icon:Library,count:126},{id:"rules",label:"공통 기준",icon:BookOpen,count:5},{id:"sources",label:"출처 현황",icon:Radio,count:12}].map(n=><button key={n.id} className={`nav-item ${tab===n.id?"active":""}`} onClick={()=>nav(n.id)} aria-current={tab===n.id?"page":undefined}><n.icon size={18}/><span>{n.label}</span><em>{n.count}</em></button>)}</nav>
      <p className="nav-label">MONITORED COMPANIES</p><div className="company-list">{Object.entries(companies).filter(([id])=>id!=="all").map(([id,name])=><button key={id} onClick={()=>{setCompany(id);nav("issues");}}><i className={`company-dot ${id}`}/>{name}<ChevronRight size={14}/></button>)}</div>
      <div className="sidebar-bottom"><span className="step-tag">PUBLIC DISCLOSURE</span><h4>변화를 살펴보고,<br/>원문을 확인하세요.</h4><p>공식 공시와 점검 근거를<br/>누구나 열람할 수 있습니다.</p><span className="version">규칙 v{data.ruleVersion}</span></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div><button className="mobile-menu icon-btn" onClick={()=>setNavOpen(!navOpen)} aria-label="메뉴 열기"><Menu size={20}/></button><span>워크스페이스</span><ChevronRight size={14}/><b>{{issues:"우선 점검",archive:"공시 보관함",rules:"공통 기준",sources:"출처 현황"}[tab]}</b></div><span className="snapshot-date"><i/>자료 기준 2026.10.16</span></header>
    <main><div className="page-heading"><div><p className="eyebrow">DISCLOSURE INTELLIGENCE</p><h1>{{issues:"놓치지 말아야 할 공시 포인트",archive:"공시를 모아, 흐름을 한눈에",rules:"작성 전에 확인할 공통 기준",sources:"정보의 출처와 확인 범위"}[tab]}</h1><p className="subtitle">{{issues:"변경사항에서 근거 확인까지, 회사별 점검을 이어가세요.",archive:"공식 검색 목록을 날짜와 회사별로 찾아보고 원문으로 연결합니다.",rules:"시행일, 적용조건과 확인 수준을 함께 살펴보세요.",sources:"접근 가능 여부와 검증 범위를 함께 관리합니다."}[tab]}</p></div><button className="secondary" onClick={()=>download("공시검토실_2026-10-16.json",{snapshot:data,exportedAt:new Date().toISOString()})}><Download size={16}/>자료 내보내기</button></div>
    <div className="notice"><CircleAlert size={18}/><p><strong>공개 열람용 검토 자료입니다.</strong> 2026.10.16 기준 수집 자료이며, 자동 갱신·메일 발송은 연결 전입니다. 내부 초안 확인과 담당자 판단이 필요합니다.</p><span>공개판</span></div>
    {(tab==="issues"||tab==="archive")&&<div className="company-tabs" aria-label="회사 필터">{Object.entries(companies).map(([id,name])=><button key={id} onClick={()=>setCompany(id)} className={company===id?"selected":""}>{name}<span>{tab==="archive"?data.filings.filter(f=>id==="all"||f.company_id===id).length:data.findings.filter(f=>id==="all"||f.company_id===id).length}</span></button>)}</div>}
    {tab==="issues"&&<><div className="metrics"><div><span>우선 점검 <i className="metric-dot"/></span><b>{scopeIssues.filter(f=>f.priority==="P1").length}<small>건</small></b><p>P1 · 제출본 확정 전 확인</p></div><div><span>정정 검토 후보</span><b>{scopeIssues.filter(f=>f.candidate).length}<small>건</small></b><p>추가 정정 필요는 미확정</p></div><div><span>필수 수정 확정</span><b>0<small>건</small></b><p>내부 초안 대조 전</p></div><div><span>공시 보관함</span><b>{data.filings.filter(f=>company==="all"||f.company_id===company).length}<small>건</small></b><p>정정 포함 · 공식 검색 목록</p></div></div>
      <div className="section-heading"><div><h2>회사별 점검 목록 <span>{issues.length}</span></h2><p>P1 우선 점검 · P2 일반 점검 / 중요도와 정정 필요성은 별도 판단합니다.</p></div><button className={`candidate-toggle ${onlyCandidates?"on":""}`} onClick={()=>setOnlyCandidates(!onlyCandidates)} aria-pressed={onlyCandidates}><CircleAlert size={15}/>정정 검토 후보만</button></div>
      <div className="filterbar"><label className="search"><Search size={17}/><input aria-label="점검 항목 검색" value={q} onChange={e=>setQ(e.target.value)} placeholder="제목, 내용, 근거로 검색"/></label><select aria-label="중요도" value={priority} onChange={e=>setPriority(e.target.value)}><option value="all">모든 중요도</option><option value="P1">P1 우선 점검</option><option value="P2">P2 일반 점검</option></select><button className="icon-btn" onClick={reset} aria-label="필터 초기화"><RotateCw size={16}/></button></div>
      <div className="issue-list">{issues.map(f=><button className="issue-row" key={f.id} onClick={()=>openDetail(f)}><span className={`priority ${f.priority}`}>{f.priority}</span><div className="issue-main"><div className="issue-meta"><span className="company-name">{companies[f.company_id]}</span><span>{f.date.replaceAll("-",".")}</span>{f.candidate&&<span className="correction-chip">정정 검토 후보</span>}</div><h3>{f.title}</h3><p>{f.instructions}</p><div className="issue-foot"><span><FileText size={12}/>{f.evidence.length}개 근거</span><span>필수 점검</span></div></div><div className="issue-side"><span className="status">미승인 자료</span><ChevronRight size={19}/></div></button>)}{issues.length===0&&<div className="empty"><Search size={28}/><h3>조건에 맞는 점검 항목이 없습니다.</h3><button className="secondary" onClick={reset}>필터 초기화</button></div>}</div></>}
    {tab==="archive"&&<><div className="archive-summary"><Library size={24}/><div><b>2026년 공식 공시 목록</b><p>2026.01.01–10.16 · 정정 포함 126건 / 전체 본문 검토 완료를 뜻하지 않습니다.</p></div><span>{filings.length}건 표시</span></div><div className="filterbar"><label className="search"><Search size={17}/><input aria-label="공시 검색" value={q} onChange={e=>setQ(e.target.value)} placeholder="보고서명, 접수번호 검색"/></label><label className="date-label">시작<input aria-label="시작일" type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label><label className="date-label">종료<input aria-label="종료일" type="date" value={to} onChange={e=>setTo(e.target.value)}/></label><button className="icon-btn" onClick={reset} aria-label="검색 초기화"><RotateCw size={16}/></button></div><div className="table-scroll archive-table"><table><thead><tr><th>접수일</th><th>회사</th><th>공시명</th><th>접수번호</th><th>원문</th></tr></thead><tbody>{filings.slice((page-1)*15,page*15).map(f=><tr key={f.receipt_no}><td>{f.received_date.replaceAll("-",".")}</td><td>{companies[f.company_id]}</td><td><b>{f.title}</b></td><td className="mono">{f.receipt_no}</td><td><a href={f.url} target="_blank" rel="noopener noreferrer" aria-label={`${f.title} DART 원문 열기`}><ArrowUpRight size={18}/></a></td></tr>)}</tbody></table>{!filings.length&&<div className="empty">조건에 맞는 공시가 없습니다.</div>}</div><div className="pagination"><span>{filings.length}건 중 {filings.length?((page-1)*15+1):0}–{Math.min(page*15,filings.length)}</span><div><button disabled={page===1} onClick={()=>setPage(p=>p-1)}>이전</button><span>{page} / {Math.max(1,Math.ceil(filings.length/15))}</span><button disabled={page*15>=filings.length} onClick={()=>setPage(p=>p+1)}>다음</button></div></div></>}
    {tab==="rules"&&<><div className="section-heading"><div><h2>보편 · 공통 적용 검토</h2><p>아래 자료는 법령·서식 참고 기준입니다. 회사별 필수 수정 확정 항목이 아닙니다.</p></div></div><div className="rule-grid">{data.rules.map((r,i)=><article className="rule-card" key={r.id}><div className="rule-top"><span>0{i+1}</span><BookOpen size={21}/></div><h3>{r.title}</h3><p>{ruleNotes[r.id]}</p><div className="rule-card-foot"><span>{(r as any).effective_date?`시행 ${(r as any).effective_date}`:"선정 자료 확인"}</span><a href={r.notice_url} target="_blank" rel="noopener noreferrer">공식 안내 <ArrowUpRight size={15}/></a></div></article>)}</div></>}
    {tab==="sources"&&<><div className="section-heading"><div><h2>공식 출처 12개 경로</h2><p>기준일 당시 접근 결과입니다. 운영 수집기의 실시간 정상 상태를 나타내지 않습니다.</p></div></div><div className="source-grid">{data.sources.map(s=><article className="source-card" key={s.id}><div><Radio size={18}/><span className={/timeout|login_required|not_validated|not_configured/.test(s.verification_status)?"source-limited":"source-checked"}>{s.id==="OPENDART"?"API 미연결":s.id==="KRX_RULES"?"접근 시간초과":s.id==="KLCA_LAWS"?"상세 로그인 필요":s.id==="LAW_CENTER"?"본문 미검증":"선정 범위 확인"}</span></div><h3>{s.name}</h3><p>{s.note}</p><a href={s.url} target="_blank" rel="noopener noreferrer">공식 사이트 <ArrowUpRight size={15}/></a></article>)}</div></>}
    <footer><span>CKD DISCLOSURE DESK</span><p>공식 자료 기반 · 미승인 검토 자료 · 공개 열람</p><span>SNAPSHOT 2026.10.16</span></footer>
    </main></div>
    {selected&&<div className="detail-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)closeDetail();}}><section className="detail-panel" role="dialog" aria-modal="true" aria-labelledby="detail-title"><div className="detail-top"><span>점검 상세 <ChevronRight size={14}/><span className="mono">{selected.id}</span></span><button className="icon-btn" onClick={closeDetail} aria-label="상세 닫기" autoFocus><X size={22}/></button></div><div className="detail-content"><div className="detail-badges"><span className={`priority ${selected.priority}`}>{selected.priority}</span><span>{companies[selected.company_id]}</span><span className="muted">미승인 검토 자료</span></div><h2 id="detail-title">{selected.title}</h2><p className="detail-date">공시 근거일 {selected.date} · 규칙 v{selected.rule_version}</p><div className="action-box"><span>작성자가 확인할 내용</span><p>{selected.instructions}</p></div><h3 className="detail-label">확인한 변화·불일치</h3><FactView f={selected}/><div className="decision-note"><CircleAlert size={16}/><div><b>{selected.correction_status}</b><p>내부 초안 미확인 · 필수 수정 확정 0건. 담당자 확인 전이며 추가 정정 필요를 확정하지 않았습니다.</p></div></div><h3 className="detail-label">원문 근거 <span>{selected.evidence.length}</span></h3><div className="evidence-list">{selected.evidence.map((e,i)=><article key={i}><div className="evidence-header"><b>{e.region==="attachment_image"?"추가 첨부 이미지":e.region==="correction_summary"?"정정 요약":"공시 본문"}</b><a href={e.url} target="_blank" rel="noopener noreferrer">원문 열기 <ArrowUpRight size={14}/></a></div><p className="location">{e.receipt_no} · {e.location}</p><blockquote>{e.excerpt}</blockquote>{e.region==="attachment_image"&&<p className="hint">AI가 선정 필드를 시각 확인했습니다. 담당자 승인·날인 진위 검증은 미완료입니다.</p>}<details><summary>증거 식별값</summary><code>{e.sha256}</code></details></article>)}</div><div className="public-review-note"><b>공개 자료 열람</b><p>개인별 검토 메모·담당자·업무 상태는 이 공개 페이지에 포함하지 않습니다. 자료의 변경·확정 여부는 원문과 담당자 검토로 확인하세요.</p><a href="https://ckd-disclosure-desk.yulemu1351.chatgpt.site" target="_blank" rel="noopener noreferrer">내부 검토 공간으로 이동 <ArrowUpRight size={14}/></a></div></div></section></div>}
  </div>;
}
