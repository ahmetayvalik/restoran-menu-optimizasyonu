import RuleExplanation from "./RuleExplanation";
import tr from "../i18n";

function getComment(rule) {
  const lift =
    rule.lift !== undefined && rule.lift !== null
      ? Number(rule.lift)
      : Number(rule.satis_artirma_carpani || 0);

  if (lift >= 1.5) {
    return tr.resultCommentStrong;
  }

  return tr.resultCommentSoft;
}

function ResultCard({ rule, index }) {
  const antecedentLabel = rule.antecedent || rule.ana_urunler?.join(", ") || "-";
  const consequentLabel = rule.consequent || rule.yaninda_satilacak_urun?.join(", ") || "-";
  const confidenceValue =
    rule.confidence !== undefined && rule.confidence !== null
      ? Math.round(Number(rule.confidence) * 100)
      : Math.round(Number(rule.guven_orani_yuzde || 0));
  const liftValue =
    rule.lift !== undefined && rule.lift !== null
      ? Number(rule.lift)
      : Number(rule.satis_artirma_carpani || 0);
  const supportValue = rule.support !== undefined && rule.support !== null ? rule.support : "-";

  return (
    <article className="result-card glass-card">
      <div className="result-card-top">
        <span className="result-rank">#{index + 1}</span>
        <span className="result-badge">{tr.resultBadge}</span>
      </div>

      <div className="result-group">
        <label>{tr.mainProduct}</label>
        <strong>{antecedentLabel}</strong>
      </div>

      <div className="result-group">
        <label>{tr.sideProduct}</label>
        <strong>{consequentLabel}</strong>
      </div>

      <div className="stats-grid">
        <div className="stat-chip">
          <span>{tr.statsBuyRate}</span>
          <strong>%{confidenceValue}</strong>
        </div>
        <div className="stat-chip">
          <span>{tr.statsInterest}</span>
          <strong>{liftValue}</strong>
        </div>
        <div className="stat-chip">
          <span>{tr.statsVisibility}</span>
          <strong>{supportValue}</strong>
        </div>
      </div>

      <p className="result-comment">{getComment(rule)}</p>
      <RuleExplanation rule={rule} />
    </article>
  );
}

function EmptyState({ title, message, eyebrow = tr.resultArea }) {
  return (
    <div className="empty-state glass-card">
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{message}</p>
    </div>
  );
}

export default function ResultsSection({ data, loading, isEmpty, placeholderMessage }) {
  if (loading) {
    return (
      <section className="results-section">
        <EmptyState
          eyebrow={tr.analysisEyebrow}
          title={tr.resultsLoadingTitle}
          message={tr.resultsLoadingMessage}
        />
      </section>
    );
  }

  if (isEmpty) {
    return (
      <section className="results-section">
        <EmptyState
          eyebrow={tr.noResult}
          title={tr.noDisplayableResult}
          message={placeholderMessage}
        />
      </section>
    );
  }

  if (!data?.results?.length) {
    return (
      <section className="results-section">
        <EmptyState title={tr.resultsNoAnalysis} message={placeholderMessage} />
      </section>
    );
  }

  return (
    <section className="results-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{tr.resultsEyebrow}</span>
          <h2>{tr.resultsTitle}</h2>
        </div>
        <div className="results-summary glass-card">
          <span>{tr.resultsRulesFound}</span>
          <strong>{data.rules_found}</strong>
        </div>
      </div>

      <div className="results-grid">
        {data.results.map((rule, index) => (
          <ResultCard
            key={`${rule.antecedent || rule.ana_urunler?.join("-") || "rule"}-${index}`}
            rule={rule}
            index={index}
          />
        ))}
      </div>
    </section>
  );
}
