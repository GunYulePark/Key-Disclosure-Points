import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import data from "./company-preparation.json";
import "./company-preparation.css";

const format = new Intl.NumberFormat("ko-KR");
const amount = (value: number | null) => value === null ? "해당 없음" : format.format(value);

export default function CompanyPreparation() {
  const [selected, setSelected] = useState("ckd");
  const company = data.companies.find(item => item.id === selected) ?? data.companies[0];
  return <div className="prep-panel">
    <div className="company-tabs" aria-label="준비사항 회사 선택">
      {data.companies.map(item => <button key={item.id} className={item.id === selected ? "selected" : ""}
        aria-pressed={item.id === selected} onClick={() => setSelected(item.id)}>{item.name}</button>)}
    </div>
    <section className="case-card prep-card">
      <h2>{company.name} 자산총계</h2>
      <p className="prep-note">단위 백만원 · 2조원 적용은 최근 사업연도 말 기준 및 조항별 산정 범위·예외를 확인합니다.</p>
      <div className="table-scroll"><table aria-label="자산총계 비교">
        <thead><tr><th>기준일</th><th>연결</th><th>별도·개별</th></tr></thead>
        <tbody>
          <tr><th scope="row">2025.12.31</th><td>{amount(company.assets.consolidatedPrior)}</td><td>{amount(company.assets.separatePrior)}</td></tr>
          <tr><th scope="row">2026.09.30</th><td>{amount(company.assets.consolidatedQuarter)}</td><td>{amount(company.assets.separateQuarter)}</td></tr>
        </tbody>
      </table></div>
      {company.id === "ckd" && <p className="prep-note">3분기 자산과 2조원의 차이는 연결 약 {format.format(Math.round((2_000_000 - (company.assets.consolidatedQuarter ?? 0)) / 100))}억원, 별도 약 {format.format(Math.round((2_000_000 - company.assets.separateQuarter) / 100))}억원입니다.</p>}
      <a className="case-common-link" href={company.source} target="_blank" rel="noreferrer">DART 분기보고서 요약재무정보 <ArrowUpRight size={14} aria-hidden/></a>
    </section>
    <section className="case-card prep-card">
      <h2>지금 준비할 사항</h2>
      <p className="prep-note">P1 우선 점검 · P2 일반 점검</p>
      <ul className="prep-list">{company.actions.map(item => <li key={item.title}>
        <span className={"priority " + item.priority}>{item.priority}</span>
        <div><h3>{item.title}</h3><p>{item.action}</p>
          <a className="case-common-link" href={"#cases-" + item.case}>관련 사례</a>
        </div>
      </li>)}</ul>
    </section>
    {company.id === "ckd" && <section className="case-card prep-card">
      <h2>2조원에 해당할 때 준비할 주총 안건</h2>
      <p className="prep-note">종근당 우선 준비 · 회사별 적용은 결산과 법정 소집·선임 절차에 따라 확정합니다.</p>
      <ul className="prep-list">{data.thresholdTopics.map(item => <li key={item.title}>
        <div><h3>{item.title}</h3><p>{item.action}</p>
          <div className="prep-links"><a className="case-common-link" href={item.source} target="_blank" rel="noreferrer">{item.article}</a>
            <a className="case-common-link" href={"#cases-" + item.case}>관련 사례</a></div>
        </div>
      </li>)}</ul>
    </section>}
    <section className="case-card prep-card">
      <h2>공통 · 2027년 제출 기업지배구조보고서</h2>
      <ul className="prep-list">{data.commonGovernance.topics.map(item => <li key={item.title}>
        <div><h3>{item.title}</h3><p>{item.action}</p></div>
      </li>)}</ul>
      <a className="case-common-link" href={data.commonGovernance.source} target="_blank" rel="noreferrer">금융위원회 가이드라인 개정 <ArrowUpRight size={14} aria-hidden/></a>
    </section>
  </div>;
}
