import {useState} from 'react';
import type {OperationState} from './operations-types';
const statuses:Record<string,string>={complete:'선정 경로 수집 완료',partial:'일부 경로 수집 실패',failed:'수집 실패',ok:'성공'};
const names:Record<string,string>={common:'공통 기준',ckd:'종근당',hold:'종근당홀딩스',kb:'경보제약'};
const kinds:Record<string,string>={filing:'새 공시',filing_metadata:'공시 목록 변경',notice:'게시물·첨부 목록 변경',notice_backlog:'기준선의 미검토 자료',document_change:'첨부 원파일 변경'};
const format=(v?:string|null)=>v?new Date(v).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}):'성공 기록 없음';
export function collectionOverdue(last:string,now=Date.now()){
 const base=new Date(Date.parse(last)+9*3600000);
 for(let day=0;day<9;day++){
  const local=new Date(Date.UTC(base.getUTCFullYear(),base.getUTCMonth(),base.getUTCDate()+day,8));
  const scheduled=local.getTime()-9*3600000;
  if(local.getUTCDay()!==0&&local.getUTCDay()!==6&&scheduled>Date.parse(last))return now>scheduled+3*3600000;
 }
 return true;
}
export default function Operations({data,error,onReload}:{data:OperationState|null;error:string;onReload:()=>void}){
 const [company,setCompany]=useState('all'),[kind,setKind]=useState('all');
 if(!data)return <section className="operations-empty"><h2>수집 상태를 확인하고 있습니다.</h2><p role="status">{error||'공개 운영 기록을 불러오는 중…'}</p><button className="secondary" onClick={onReload}>다시 불러오기</button></section>;
 const overdue=collectionOverdue(data.lastAttemptAt),queue=data.queue.filter(q=>(company==='all'||q.company_id===company)&&(kind==='all'||q.kind===kind));
 return <section className="operations"><div className="ops-banner"><div><span className={`ops-state ${data.lastRunStatus}`}>{statuses[data.lastRunStatus]}</span>{overdue&&<span className="ops-stale">예정 점검 시각 경과 · 실행 이력 확인 필요</span>}</div><h2>평일 오전 8시 · PC 없이 클라우드에서 점검</h2><p>한국시간 월~금 08:00 예약입니다. GitHub 작업 대기에 따라 시작이 지연될 수 있습니다. 이 저장소의 갱신은 한 번에 하나씩 처리합니다.</p><div className="ops-buttons"><a className="secondary" href="https://github.com/GunYulePark/Key-Disclosure-Points/actions/workflows/update-disclosures.yml" target="_blank" rel="noopener noreferrer">실행 이력·수동 갱신 (GitHub) ↗</a><button className="secondary" onClick={onReload}>상태 다시 읽기</button></div></div>
  {error&&<p role="status" className="ops-stale">{error} 마지막으로 읽은 상태를 표시합니다.</p>}
  <div className="ops-metrics"><article><span>최근 수집 시도</span><b>{format(data.lastAttemptAt)}</b></article><article><span>선정 경로 전체 성공</span><b>{format(data.lastCompleteAt)}</b></article><article><span>내용·적용 검토 대기</span><b>{data.queue.length}건</b></article><article><span>분석 자료 기준</span><b>{data.reviewBaseline.asOf} · v{data.reviewBaseline.ruleVersion}</b></article></div>
  <div className="engine-note"><h3>어떤 엔진이 무엇을 하나요?</h3><div className="table-scroll"><table><thead><tr><th>단계</th><th>실행 위치·엔진</th><th>현재 상태</th></tr></thead><tbody><tr><td>공시·규정 수집</td><td>GitHub Actions · Python</td><td>예약 실행·공개 원문 비교</td></tr><tr><td>변경 탐지</td><td>접수번호·목록·첨부 SHA-256 비교</td><td>검토 대기 목록 적재</td></tr><tr><td>규정 해석·회사별 조치</td><td>이 대화에서 Codex가 검토</td><td>무인 AI 엔진 미연결 · 제미나이 사용 없음</td></tr><tr><td>메일 발송</td><td>비공개 공간의 초안·승인·EML</td><td>발신계정 추후 설정 · 자동 발송 없음</td></tr></tbody></table></div><p>이 PC의 자원이나 Codex 대화 사용한도를 소모해 예약 작업을 실행하는 방식은 아닙니다. 다른 저장소의 작업과는 별개이며 GitHub 계정의 동시 실행 한도·대기열은 적용될 수 있습니다.</p></div>
  <div className="section-heading"><div><h2>새 자료·변경 검토 대기 <span>{queue.length}</span></h2><p>탐지 결과이며 수정 의무·정정 필요·시행 여부를 확정한 항목이 아닙니다.</p></div></div><div className="filterbar"><select aria-label="수집 검토 회사" value={company} onChange={e=>setCompany(e.target.value)}><option value="all">전체 범위</option>{Object.entries(names).map(([id,name])=><option value={id} key={id}>{name}</option>)}</select><select aria-label="수집 변경 종류" value={kind} onChange={e=>setKind(e.target.value)}><option value="all">모든 변경 종류</option>{Object.entries(kinds).map(([id,name])=><option value={id} key={id}>{name}</option>)}</select></div>
  <div className="ops-queue">{queue.map(q=><article key={q.id}><div><span>{names[q.company_id]}</span><span>{kinds[q.kind]||q.kind}</span><span>내용·적용 미검토</span></div><h3>{q.title}</h3><p>{q.review}</p><p className="hint">원문 일자 {q.date} · 처음 탐지 {format(q.firstSeenAt)}</p><a href={q.url} target="_blank" rel="noopener noreferrer">공식 원문 확인 ↗</a>{q.attachments&&<details><summary>첨부 목록 {q.attachments.length}개 · 개별 본문 해석 전</summary>{q.attachments.map(a=><p key={a.url}><a href={a.url} target="_blank" rel="noopener noreferrer">{a.title} ↗</a></p>)}</details>}<details><summary>변경 전후 식별정보</summary><pre>{JSON.stringify({before:q.before,after:q.after},null,2)}</pre></details></article>)}{!queue.length&&<p className="ops-no-change">현재 선택 범위에 새 검토 후보가 없습니다. 미수집 경로·미확인 본문에 변경이 없다는 뜻은 아닙니다.</p>}</div>
  <h2 className="ops-heading">수집 경로별 상태</h2><div className="ops-sources">{data.sources.map(s=><article key={s.id}><h3>{s.title}</h3><span className={`ops-state ${s.status}`}>{s.status==='ok'?'성공':'실패 · 기존 자료 유지'}</span><p>최근 성공: {format(s.lastSuccessAt)}</p>{s.error&&<p className="ops-stale">오류: {s.error}</p>}<p className="hint">{typeof s.detail?.scope==='string'?s.detail.scope:s.id.startsWith('filings-')?'정정 포함 공시 목록·페이지 수/건수 대사 · 본문은 별도 검토':'선정 경로'}</p></article>)}</div>
  <h2 className="ops-heading">실행 이력 (최근 30회)</h2><div className="table-scroll"><table><thead><tr><th>한국시간</th><th>결과</th><th>성공 경로</th><th>추가 후보</th><th>로그</th></tr></thead><tbody>{data.runs.map(r=><tr key={r.id}><td>{format(r.at)}</td><td>{statuses[r.status]}</td><td>{r.ok}/{r.total}</td><td>{r.newCandidates}</td><td>{r.workflowRunUrl?<a href={r.workflowRunUrl} target="_blank" rel="noopener noreferrer">GitHub ↗</a>:'로컬 검증'}</td></tr>)}</tbody></table></div>
  <div className="ops-limits"><h3>현재 수집 범위와 남은 연결</h3>{data.limits.map(x=><p key={x}>{x}</p>)}</div>
 </section>;
}
