import { getCategoryColor } from "../constants/categoryColors";
import tr from "../i18n";

function InterpretationBadge({ interpretation }) {
  const normalized = String(interpretation).toLowerCase();
  let className = "interpretation-badge interpretation-soft";
  let label = tr.weakTrend;

  if (normalized.includes("guclu") || normalized.includes("güçlü")) {
    className = "interpretation-badge interpretation-strong";
    label = tr.strongHabit;
  } else if (normalized.includes("orta")) {
    className = "interpretation-badge interpretation-medium";
    label = tr.clearTrend;
  }

  return <span className={className}>{label}</span>;
}

function percent(value) {
  return Math.round(Number(value) * 100);
}

function plusPercent(value) {
  const rounded = Math.round(Number(value));
  return rounded >= 0 ? String(rounded) : `-${Math.abs(rounded)}`;
}

export default function BayesAnalysisTab({ bayesRules }) {
  return (
    <div className="tab-stack">
      {bayesRules.map((rule) => (
        <article
          key={`${rule.antecedent}-${rule.consequent}`}
          className="bayes-card glass-card"
        >
          <div className="bayes-card-top">
            <div className="bayes-title">
              <strong>{tr.customerBuys.replace("{item}", rule.antecedent)}</strong>
              <div className="category-flow compact-flow">
                <span
                  className="category-tag"
                  style={{
                    borderColor: getCategoryColor(rule.antecedent_category),
                    color: getCategoryColor(rule.antecedent_category)
                  }}
                >
                  {rule.antecedent_category}
                </span>
                <span className="flow-arrow">→</span>
                <span
                  className="category-tag"
                  style={{
                    borderColor: getCategoryColor(rule.consequent_category),
                    color: getCategoryColor(rule.consequent_category)
                  }}
                >
                  {rule.consequent_category}
                </span>
              </div>
            </div>
            <InterpretationBadge interpretation={rule.interpretation} />
          </div>

          <div className="probability-flow">
            <span>{tr.generalChance.replace("{pct}", String(percent(rule.prior_probability)))}</span>
            <span className="flow-arrow">→</span>
            <span>
              {tr.withThisItem.replace(
                "{pct}",
                String(percent(rule.posterior_probability))
              )}
            </span>
          </div>

          <p className="belief-update">
            {tr.interestIncrease.replace("{pct}", plusPercent(rule.belief_update_pct))}
          </p>
        </article>
      ))}

      <p className="belief-update">* {tr.weakCombinationNote}</p>
    </div>
  );
}
