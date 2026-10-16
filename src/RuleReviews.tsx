import {useState} from 'react';
import reviews from './rule-reviews.json';

export default function RuleReviews({compact=false}:{compact?:boolean}) {
 const [company,setCompany]=useState('all');
 return <section className="review-library" id="rules-bio">
  <div className="section-heading"><div><h2>규정 변경 → 회사별 반영사항</h2><p>원문·후속 기준·회사 공시를 연결한 검토 기록입니다. 중요도와 법적 수정 의무를 구분합니다.</p></div></div>
  {reviews.map(review=><article className="review-document" key={review.id}>
   <div className="review-heading"><span className="priority P1">P1</span><div><h3>{review.title}</h3><p>배포 {review.distributed_date} · 보도 {review.release_date} · 후속 모범사례 게시 {review.guidance_posted_date}</p></div></div>
   <p className="review-status">{review.legal_status}</p>
   <div className="company-tabs" aria-label="규정 적용 회사">{[['all','전체'],...review.companies.map(c=>[c.id,c.name])].map(([id,name])=><button key={id} className={company===id?'selected':''} onClick={()=>setCompany(id)}>{name}</button>)}</div>
   <div className="company-review-grid">{review.companies.filter(c=>company==='all'||c.id===company).map(c=><article key={c.id}>
    <h4>{c.name} <span>반영 검토 · 정정 미확정</span></h4><b>현재 공시에서 확인</b><p>{c.observed}</p><b>작성자가 확인·보완할 부분</b><p>{c.action}</p><p className="hint">{c.limitation}</p><a href={c.evidence.url} target="_blank" rel="noopener noreferrer">{c.evidence.receipt_no} · {c.evidence.section} ↗</a>
   </article>)}</div>
   <details open={!compact}><summary>변경 기준 {review.rules.length}개 · 전후 내용과 조치 확인</summary><div className="change-grid">{review.rules.filter(r=>company==='all'||review.companies.find(c=>c.id===company)?.rule_ids.includes(r.id)||r.priority==='P2').map(r=><article className="change-card" key={r.id}>
    <div><span className={`priority ${r.priority}`}>{r.priority}</span><span className="change-state">{r.state}</span></div><h4>{r.title}</h4><dl><dt>종전 관행·확인할 위험</dt><dd>{r.before}</dd><dt>변경·구체화된 기준</dt><dd>{r.after}</dd><dt>실무 조치</dt><dd>{r.action}</dd></dl><p className="hint">근거: {r.location}</p>
   </article>)}</div></details>
   <p className="hint">확인 범위: {review.coverage}</p><a href={review.guidance_url} target="_blank" rel="noopener noreferrer">금융감독원 후속 모범사례 원문 ↗</a>
  </article>)}
 </section>;
}
