import { ArrowUpRight, CircleAlert, FileText } from 'lucide-react';
import data from './snapshot.json';

export default function TreasuryReview() {
  const r=data.treasuryReview;
  return <div className="treasury-review">
    <div className="treasury-callout"><CircleAlert size={18}/><div><b>{r.headline}</b><p>{r.summary}</p></div></div>
    <details className="treasury-details" open={typeof window!=='undefined'&&window.location.hash==='#rules-treasury'}>
      <summary>회사별 적용·필수 점검·PDF 근거 펼치기</summary>
      <div className="treasury-body">
        <div className="review-stamp">P1 우선 점검 · {r.effective_date} 시행 · PDF·공시 대조 {r.reviewed_on}</div>
        <h4>무엇이 바뀌었나요?</h4>
        <div className="rule-comparison"><div><small>개정 전 / 회사가 사용한 생략 근거</small><p>{r.before}</p></div><div><small>현행 기준 / 작성자가 바꿔야 할 내용</small><p>{r.after}</p></div></div>
        <div className="rule-filing"><b>종근당 공시에서 실제 확인한 문구</b><p>{r.filing_evidence.location}</p><blockquote>{r.filing_evidence.excerpt}</blockquote><a href={r.filing_evidence.url} target="_blank" rel="noopener noreferrer">종근당 반기보고서 해당 본문 <ArrowUpRight size={14}/></a><p>조회한 공개 첨부 목록: {r.filing_evidence.attachment_labels_observed.join(' · ')}. 첨부 원본·내부 승인자료는 추가 대조가 필요합니다.</p></div>
        <h4>회사별 적용 판단</h4>
        <div className="table-scroll treasury-table"><table><thead><tr><th>회사·공시 근거</th><th>확인한 사실</th><th>적용·조치</th></tr></thead><tbody>{r.company_rows.map(c=><tr key={c.company_id}><td><b>{c.company}</b><br/><a href={c.url} target="_blank" rel="noopener noreferrer">{c.receipt_no} ↗</a></td><td>{c.basis}</td><td><strong>{c.judgment}</strong><p>{c.action}</p></td></tr>)}</tbody></table></div>
        <h4>보고서별 첨부 조건 — 서로 다른 문서입니다</h4>
        <div className="table-scroll treasury-table"><table><thead><tr><th>제출 보고서</th><th>자기주식보고서</th><th>자기주식보유처분계획서</th></tr></thead><tbody>{r.period_rows.map(p=><tr key={p.report}><td><b>{p.report}</b></td><td>{p.treasury}</td><td>{p.plan}</td></tr>)}</tbody></table></div>
        <p className="hint">반기·사업보고서 작성 대상 확대를 3분기 자기주식보고서 첨부 의무로 바꾸어 적용하지 않습니다. 기준일별 미교환 잔량과 문서별 제출조건을 각각 확인합니다.</p>
        <h4>작성·제출 전에 꼭 점검할 부분</h4>
        <ol className="treasury-checklist">{r.required_changes.map(c=><li key={c.title}><span className={`priority ${c.priority}`}>{c.priority}</span><div><b>{c.title}</b><p>{c.detail}</p></div></li>)}</ol>
        <h4>직접 확인한 PDF 본문·서식</h4>
        <p className="hint">아래 쪽수는 PDF 파일의 실제 페이지 번호입니다. 인쇄 쪽수가 다른 자료는 함께 표시했습니다. 파일 전체 검토 완료가 아닌, 표시한 관련 조항·서식의 대조 결과입니다.</p>
        <div className="treasury-documents">{r.documents.map(d=><article key={d.key}><div><FileText size={17}/><b>{d.title}</b></div><p>PDF {d.pdf_pages.join(', ')}쪽 · {d.location}</p><p>{d.summary}</p><a href={d.url+'#page='+d.pdf_pages[0]} target="_blank" rel="noopener noreferrer">공식 PDF 원문 <ArrowUpRight size={14}/></a><details><summary>원파일 SHA-256</summary><code>{d.sha256}</code></details></article>)}</div>
        <details className="pdf-excerpts"><summary>PDF 원문 페이지 이미지 보기 (3장)</summary><div>{r.figures.map(f=><figure key={f.src}><a href={'./'+f.src} target="_blank" rel="noopener noreferrer"><img src={'./'+f.src} alt={f.caption} loading="lazy"/></a><figcaption>{f.caption}</figcaption></figure>)}</div></details>
        <p className="review-limit">{r.limits}</p>
      </div>
    </details>
  </div>;
}
