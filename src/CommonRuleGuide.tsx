import {useEffect} from "react";
import {ArrowUpRight} from "lucide-react";
import guides from "./common-rule-guide.json";
import "./common-rule-guide.css";

export const commonRuleCount = guides.length;

export default function CommonRuleGuide() {
  useEffect(() => {
    function openLinkedGuide() {
      const guide = guides.find(item => window.location.hash === "#rules-" + item.id);
      if (!guide) return;
      const section = document.getElementById("rules-" + guide.id);
      const details = section?.querySelector("details");
      if (details) details.open = true;
    }
    openLinkedGuide();
    window.addEventListener("hashchange", openLinkedGuide);
    return () => window.removeEventListener("hashchange", openLinkedGuide);
  }, []);
  return <section className="common-rule-guide" aria-label="공통 기준 실무 점검">
    <nav className="common-rule-index" aria-label="공통 기준 항목">
      {guides.map(guide => <a key={guide.id} href={"#rules-" + guide.id}>{guide.shortTitle}</a>)}
      <a href="#rules-treasury">자기주식</a>
      <a href="#rules-bio">제약·바이오</a>
      <a href="#rules-format_current">작성기준 판본</a>
    </nav>
    {guides.map(guide => <article key={guide.id} id={"rules-" + guide.id} className="case-card common-rule-entry">
      <header>
        <h2>{guide.title}</h2>
        <p className="common-rule-scope">{guide.scope}</p>
      </header>
      <p>{guide.summary}</p>
      <details>
        <summary>판단 기준과 확인 서류</summary>
        <dl className="case-checks">
          {guide.checks.map(check => <div key={check.title}>
            <dt>{check.title}</dt><dd>{check.action}</dd>
          </div>)}
        </dl>
        <ul className="case-sources" aria-label="공식 근거">
          {guide.sources.map(source => <li key={source.url}>
            <a href={source.url} target="_blank" rel="noreferrer">{source.label}<ArrowUpRight size={13} aria-hidden/></a>
          </li>)}
        </ul>
      </details>
      <div className="common-rule-related">
        {guide.related.map(link => <a className="case-common-link" href={link.href} key={link.href}>{link.label}</a>)}
      </div>
    </article>)}
  </section>;
}
