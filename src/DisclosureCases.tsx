import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import caseData from "./disclosure-cases.json";
import "./disclosure-cases.css";

const companies = {
  ckd: "종근당",
  hold: "종근당홀딩스",
  kb: "경보제약",
};
type Source = { label: string; url: string };
type FilingComparison = {
  company: string;
  filing: string;
  beforeLabel?: string;
  afterLabel?: string;
  before: string;
  after: string;
  sources: Source[];
};
type DisclosureCase = {
  id: string;
  title: string;
  priority: string;
  status: string;
  rule: string;
  ruleSources: Source[];
  commonRule?: string;
  examples: FilingComparison[];
  checks: { company: string; action: string; sources?: Source[] }[];
};
const cases: DisclosureCase[] = caseData;
const priorityLabels: Record<string, string> = {
  P1: "제출 전 우선 확인",
  P2: "적용 조건·이력 확인",
};

function SourceLinks({ sources }: { sources: Source[] }) {
  return <ul className="case-sources">
    {sources.map(source => <li key={source.url}>
      <a href={source.url} target="_blank" rel="noopener noreferrer">
        {source.label} <ArrowUpRight size={14} aria-hidden="true" />
      </a>
    </li>)}
  </ul>;
}

export default function DisclosureCases() {
  const [company, setCompany] = useState("all");

  return <div className="disclosure-cases">
    <div className="case-controls">
      <nav aria-label="사례 바로가기">
        {cases.map(item => <a href={"#cases-" + item.id} key={item.id}>{item.title}</a>)}
      </nav>
      <label>
        점검 회사
        <select value={company} onChange={event => setCompany(event.target.value)}>
          <option value="all">전체 회사</option>
          {Object.entries(companies).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
        </select>
      </label>
    </div>
    <div className="case-list">
      {cases.map(item => <article
        className="case-card"
        key={item.id}
        id={"cases-" + item.id}
        aria-labelledby={"case-title-" + item.id}
      >
        <header className="case-heading">
          <div className="case-priority">
            <span className={"priority " + item.priority}>{item.priority}</span>
            <span>{priorityLabels[item.priority]}</span>
          </div>
          <h2 id={"case-title-" + item.id}>{item.title}</h2>
          <p>{item.status}</p>
        </header>
        <section className="case-section">
          <h3>바뀐 기준</h3>
          <p>{item.rule}</p>
          <SourceLinks sources={item.ruleSources} />
          {item.commonRule && <a className="case-common-link" href={item.commonRule}>공통 기준 상세</a>}
        </section>
        <section className="case-section">
          <h3>실제 공시 비교</h3>
          {item.examples.map(example => <div className="case-example" key={example.company}>
            <div className="case-example-title"><h4>{example.company}</h4><span>{example.filing}</span></div>
            <dl className="case-comparison">
              <div><dt>{example.beforeLabel ?? "변경 전"}</dt><dd>{example.before}</dd></div>
              <div><dt>{example.afterLabel ?? "변경 후"}</dt><dd>{example.after}</dd></div>
            </dl>
            <SourceLinks sources={example.sources} />
          </div>)}
        </section>
        <section className="case-section">
          <h3>회사별 점검</h3>
          <dl className="case-checks">
            {item.checks.filter(check => company === "all" || check.company === company).map(check =>
              <div key={check.company}>
                <dt>{companies[check.company as keyof typeof companies]}</dt>
                <dd>
                  <p>{check.action}</p>
                  {check.sources && <SourceLinks sources={check.sources} />}
                </dd>
              </div>,
            )}
          </dl>
        </section>
      </article>)}
    </div>
  </div>;
}
