import tr from "../i18n";

export default function BaselineComparisonTab({ baselineComparison }) {
  const factorMatch = String(baselineComparison.bayes_approach_advantage || "").match(/(\d+(\.\d+)?)x/);
  const factorText = factorMatch ? factorMatch[1] : "";

  return (
    <div className="baseline-grid">
      <article className="baseline-card baseline-card-muted">
        <span className="eyebrow">{tr.classicApproach}</span>
        <h3>{tr.classicApproach}</h3>
        <ul className="baseline-list">
          {baselineComparison.top_popular_items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="baseline-footnote">{tr.classicDesc}</p>
      </article>

      <article className="baseline-card baseline-card-highlight">
        <span className="eyebrow">{tr.thisSystem}</span>
        <h3>{tr.thisSystem}</h3>
        <p className="baseline-advantage">
          {tr.winnerBanner.replace("{factor}", factorText)}
        </p>
        <p className="baseline-footnote">{tr.thisSystemDesc}</p>
      </article>
    </div>
  );
}
