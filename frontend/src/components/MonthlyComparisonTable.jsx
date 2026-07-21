import tr from "../i18n";

function formatFactor(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Number(value).toFixed(1)}x`;
}

function getChangeMeta(changePct) {
  if (changePct > 10) {
    return { className: "trend-up", icon: "↑", label: tr.strengthening };
  }
  if (changePct < -10) {
    return { className: "trend-down", icon: "↓", label: tr.weakening };
  }
  return { className: "trend-stable", icon: "→", label: tr.stable };
}

export default function MonthlyComparisonTable({ rows }) {
  if (!rows.length) {
    return (
      <article className="glass-card trend-card">
        <h3>{tr.monthlyComparisonTitle}</h3>
        <p className="trend-empty">{tr.noMonthlyRows}</p>
      </article>
    );
  }

  return (
    <article className="glass-card trend-card">
      <h3>{tr.monthlyComparisonTitle}</h3>
      <div className="trend-table-wrap">
        <table className="trend-table">
          <thead>
            <tr>
              <th>{tr.productPair}</th>
              <th>{tr.monthJanuary}</th>
              <th>{tr.monthFebruary}</th>
              <th>{tr.monthMarch}</th>
              <th>{tr.trend}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const change = getChangeMeta(row.change_pct);
              return (
                <tr key={row.key}>
                  <td>{row.label}</td>
                  <td>{formatFactor(row.jan_factor)}</td>
                  <td>{formatFactor(row.feb_factor)}</td>
                  <td>{formatFactor(row.mar_factor)}</td>
                  <td className={change.className}>
                    {change.icon} {change.label}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}
