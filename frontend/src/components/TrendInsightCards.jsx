import tr from "../i18n";

function InsightList({ items, renderItem, emptyText }) {
  if (!items?.length) {
    return <p className="trend-empty">{emptyText}</p>;
  }

  return (
    <ul className="trend-insight-list">
      {items.map((item, index) => (
        <li key={`${index}-${renderItem(item)}`}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

export default function TrendInsightCards({ insights }) {
  const consistentLabel = insights?.most_consistent
    ? `${insights.most_consistent.antecedent} → ${insights.most_consistent.consequent} (${Number(
        insights.most_consistent.avg_bayes_factor
      ).toFixed(1)}x)`
    : null;

  return (
    <div className="trend-insight-grid">
      <article className="glass-card trend-card">
        <h3>🚀 {tr.strongPairs}</h3>
        <InsightList
          items={insights?.rising_combinations || []}
          emptyText={tr.noStrongPairs}
          renderItem={(item) =>
            `${item.antecedent} → ${item.consequent} (+${Math.round(item.change_pct)}%)`
          }
        />
      </article>

      <article className="glass-card trend-card">
        <h3>📉 {tr.weakPairs}</h3>
        <InsightList
          items={insights?.falling_combinations || []}
          emptyText={tr.noWeakPairs}
          renderItem={(item) =>
            `${item.antecedent} → ${item.consequent} (${Math.round(item.change_pct)}%)`
          }
        />
      </article>

      <article className="glass-card trend-card">
        <h3>🆕 {tr.newlyEmerging}</h3>
        <InsightList
          items={insights?.new_in_march || []}
          emptyText={tr.noNewPairs}
          renderItem={(item) => item}
        />
      </article>

      <article className="glass-card trend-card">
        <h3>⭐ {tr.alwaysValid}</h3>
        {consistentLabel ? (
          <p className="trend-consistent">{consistentLabel}</p>
        ) : (
          <p className="trend-empty">{tr.noAlwaysValid}</p>
        )}
      </article>
    </div>
  );
}
