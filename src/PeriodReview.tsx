import review from './period-review.json';
import type {OperationState} from './operations-types';
export default function PeriodReview({operations}:{operations:OperationState|null}){
 const newer=review.companies.filter(c=>(operations?.filings||[]).some(f=>{const p=f.title.match(/(?:분기|반기|사업)보고서\s*\((\d{4}\.\d{2})\)/);return f.company_id===c.id&&p&&p[1]>=review.period&&f.receipt_no>c.receipt_no;}));
 return <section className="engine-note" aria-label="보고서"><h3>2026년 3분기</h3><p>보고 기준일 {review.reportDate}</p><div className="ops-buttons">{review.companies.map(c=><a key={c.id} href={c.url} target="_blank" rel="noopener noreferrer">{{ckd:'종근당 · 정정 분기보고서',hold:'종근당홀딩스 · 분기보고서',kb:'경보제약 · 분기보고서'}[c.id]} ↗</a>)}</div>{newer.length>0&&<p className="ops-stale" role="status">새 보고서가 수집됐습니다. 내용 반영 대기: {newer.map(c=>c.name).join(' / ')}</p>}<details><summary>자료 범위·이력</summary><p>{review.scope}</p><p>과거 반기 지적의 정정 완료 여부는 이번 분기 반영 확인과 구분합니다.</p><a href="./data/review-2026-10-16.json" target="_blank" rel="noopener noreferrer">이전 검토 자료(JSON)</a></details></section>;
}
