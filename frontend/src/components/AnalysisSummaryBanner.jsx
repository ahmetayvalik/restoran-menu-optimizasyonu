import { useEffect, useState } from "react";
import { getCategoryColor } from "../constants/categoryColors";
import tr from "../i18n";

const TIME_FILTER_META = {
  lunch: { label: tr.serviceLunch, icon: "☀️", color: "#D97706" },
  afternoon: { label: tr.serviceAfternoon, icon: "🌤", color: "#F59E0B" },
  dinner: { label: tr.serviceDinner, icon: "🌆", color: "#2563EB" },
  night: { label: tr.serviceNight, icon: "🌙", color: "#4F46E5" }
};

function CountUpValue({ value }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const numericValue = Number(value) || 0;
    const duration = 1000;
    const steps = 30;
    const increment = numericValue / steps;
    let currentStep = 0;

    setDisplayValue(0);

    const interval = setInterval(() => {
      currentStep += 1;
      if (currentStep >= steps) {
        setDisplayValue(numericValue);
        clearInterval(interval);
        return;
      }

      setDisplayValue(Math.round(increment * currentStep));
    }, duration / steps);

    return () => clearInterval(interval);
  }, [value]);

  return <strong>{displayValue}</strong>;
}

function SummaryMetric({ label, value }) {
  return (
    <div className="summary-metric glass-card">
      <span>{label}</span>
      <CountUpValue value={value} />
    </div>
  );
}

export default function AnalysisSummaryBanner({ summary }) {
  if (!summary) {
    return null;
  }

  const categories = Array.isArray(summary.categories_available)
    ? summary.categories_available.join(" · ")
    : "";
  const activeFilterColor = getCategoryColor(summary.active_category_filter);
  const timeMeta = summary.active_time_filter
    ? TIME_FILTER_META[summary.active_time_filter]
    : null;
  const hasCategoryFilter = Boolean(summary.active_category_filter);
  const hasTimeFilter = Boolean(summary.active_time_filter);

  return (
    <section className="summary-banner">
      <div className="summary-grid">
        <SummaryMetric label={tr.analyzedOrders} value={summary.total_orders} />
        <SummaryMetric label={tr.menuItems} value={summary.unique_items} />
        <SummaryMetric label={tr.detectedHabits} value={summary.rules_found} />
        <SummaryMetric label={tr.packageSuggestions} value={summary.packages_generated} />
      </div>

      <div className="summary-meta glass-card">
        <span>{tr.dateRangeSummary.replace("{date_range}", summary.date_range)}</span>
        <span>{tr.coveredCuisines.replace("{categories}", categories)}</span>
      </div>

      {hasCategoryFilter && hasTimeFilter ? (
        <div className="filter-badge-row">
          <div className="active-filter-badge active-filter-badge-neutral">
            {tr.combinedFilterBadge
              .replace("{category}", summary.active_category_filter)
              .replace("{time_icon}", timeMeta.icon)
              .replace("{time}", timeMeta.label)
              .replace("{count}", String(summary.filtered_order_count))}
          </div>
        </div>
      ) : null}

      {hasCategoryFilter && !hasTimeFilter ? (
        <div
          className="active-filter-badge"
          style={{ backgroundColor: activeFilterColor, color: "#fff" }}
        >
          {tr.categoryOnlyBadge
            .replace("{category}", summary.active_category_filter)
            .replace("{count}", String(summary.filtered_order_count))}
        </div>
      ) : null}

      {hasTimeFilter && !hasCategoryFilter ? (
        <div
          className="active-filter-badge"
          style={{ backgroundColor: timeMeta.color, color: "#fff" }}
        >
          {tr.timeOnlyBadge
            .replace("{time}", timeMeta.label)
            .replace("{count}", String(summary.time_filter_order_count))}
        </div>
      ) : null}
    </section>
  );
}
