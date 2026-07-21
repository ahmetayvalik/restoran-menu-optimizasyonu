import MonthlyComparisonTable from "./MonthlyComparisonTable";
import TrendInsightCards from "./TrendInsightCards";
import TrendLineChart from "./TrendLineChart";

function buildTrendRows(monthlyTrend) {
  const monthMaps = {};

  ["1", "2", "3"].forEach((monthKey) => {
    const rules = monthlyTrend?.months?.[monthKey]?.top_rules || [];
    monthMaps[monthKey] = new Map(
      rules.map((rule) => [
        `${rule.antecedent}->${rule.consequent}`,
        {
          label: `${rule.antecedent}\u2192${rule.consequent}`,
          antecedent: rule.antecedent,
          consequent: rule.consequent,
          factor: Number(rule.bayes_factor),
        },
      ])
    );
  });

  const keys = new Set([
    ...monthMaps["1"].keys(),
    ...monthMaps["2"].keys(),
    ...monthMaps["3"].keys(),
  ]);

  return Array.from(keys)
    .map((key) => {
      const jan = monthMaps["1"].get(key);
      const feb = monthMaps["2"].get(key);
      const mar = monthMaps["3"].get(key);
      const baseline = jan?.factor || 0;
      const finalFactor = mar?.factor || baseline;
      const changePct = baseline > 0 ? ((finalFactor - baseline) / baseline) * 100 : 0;

      return {
        key,
        label: jan?.label || feb?.label || mar?.label || key,
        jan_factor: jan?.factor ?? null,
        feb_factor: feb?.factor ?? null,
        mar_factor: mar?.factor ?? null,
        change_pct: changePct,
      };
    })
    .sort((left, right) => (right.mar_factor || 0) - (left.mar_factor || 0));
}

export default function TrendTab({ monthlyTrend }) {
  const rows = buildTrendRows(monthlyTrend);
  const chartSeries = [...rows]
    .filter((row) => row.jan_factor !== null || row.feb_factor !== null || row.mar_factor !== null)
    .map((row) => ({
      ...row,
      avg_factor:
        ((row.jan_factor || 0) + (row.feb_factor || 0) + (row.mar_factor || 0)) /
        [row.jan_factor, row.feb_factor, row.mar_factor].filter((value) => value !== null).length,
    }))
    .sort((left, right) => right.avg_factor - left.avg_factor)
    .slice(0, 5);

  return (
    <div className="tab-stack">
      <MonthlyComparisonTable rows={rows} />
      <TrendInsightCards insights={monthlyTrend?.trend_insights} />
      <TrendLineChart series={chartSeries} />
    </div>
  );
}
