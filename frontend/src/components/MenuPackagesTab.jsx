import { useMemo, useState } from "react";
import { getCategoryColor } from "../constants/categoryColors";
import { MENU_ITEM_PRICES } from "../constants/menuPrices";
import PriceStrategyBadge from "./PriceStrategyBadge";
import tr from "../i18n";

const TIME_CONTEXT_META = {
  lunch: tr.packageContextLunch,
  afternoon: tr.packageContextAfternoon,
  dinner: tr.packageContextDinner,
  night: tr.packageContextNight
};

function formatCurrency(value) {
  return `$${Number(value).toFixed(2)}`;
}

function formatPackageDescription(description) {
  return String(description)
    .replaceAll("Güçlü Bayes kanıtı", tr.strongHabit)
    .replaceAll("Orta Bayes kanıtı", tr.clearTrend)
    .replaceAll("Zayıf Bayes kanıtı", tr.weakTrend)
    .replaceAll("Guclu Bayes kaniti", tr.strongHabit)
    .replaceAll("Orta Bayes kaniti", tr.clearTrend)
    .replaceAll("Zayif Bayes kaniti", tr.weakTrend)
    .replaceAll("Güçlü alışkanlık", tr.strongHabit)
    .replaceAll("Belirgin eğilim", tr.clearTrend)
    .replaceAll("Zayıf eğilim", tr.weakTrend);
}

function getHabitBadge(bayesFactor) {
  if (bayesFactor > 1.8) {
    return { label: tr.frequentlyBoughtTogether, className: "bayes-pill bayes-strong" };
  }
  if (bayesFactor >= 1.3) {
    return { label: tr.oftenBoughtTogether, className: "bayes-pill bayes-medium" };
  }
  return { label: tr.sometimesBoughtTogether, className: "bayes-pill bayes-soft" };
}

function getOpportunityMeta(score) {
  if (score > 40) {
    return { className: "opportunity-box opportunity-high", label: tr.highOpportunity };
  }
  if (score >= 20) {
    return { className: "opportunity-box opportunity-medium", label: tr.mediumOpportunity };
  }
  return { className: "opportunity-box opportunity-low", label: tr.lowOpportunity };
}

function CategoryFlow({ from, to }) {
  const fromColor = getCategoryColor(from);
  const toColor = getCategoryColor(to);

  return (
    <div className="category-flow">
      <span className="category-tag" style={{ borderColor: fromColor, color: fromColor }}>
        {from}
      </span>
      <span className="flow-arrow">→</span>
      <span className="category-tag" style={{ borderColor: toColor, color: toColor }}>
        {to}
      </span>
    </div>
  );
}

function SortControls({ sortBy, onChange }) {
  const options = [
    { id: "strongest", label: tr.sortMostPreferred },
    { id: "valuable", label: tr.sortHighestEarning },
    { id: "hybrid", label: tr.sortBalanced }
  ];

  return (
    <div className="sort-controls">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          className={`sort-button ${sortBy === option.id ? "sort-button-active" : ""}`}
          onClick={() => onChange(option.id)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function enrichPackage(pkg, maxOpportunityScore) {
  const itemA = pkg.items[0];
  const itemB = pkg.items[1];
  const priceA = Number(MENU_ITEM_PRICES[itemA] || 0);
  const priceB = Number(MENU_ITEM_PRICES[itemB] || 0);
  const computedTotal = priceA + priceB;
  const backendTotal = Number(pkg.package_total_price || 0);
  const verifiedTotal =
    Math.abs(computedTotal - backendTotal) < 0.01 ? backendTotal : computedTotal;
  const normalizedPriceScore =
    maxOpportunityScore > 0 ? Number(pkg.price_opportunity_score) / maxOpportunityScore : 0;
  const hybridScore = Number(pkg.bayes_factor) * 0.6 + normalizedPriceScore * 0.4;

  return {
    ...pkg,
    itemPrices: [
      { name: itemA, price: priceA },
      { name: itemB, price: priceB }
    ],
    verifiedTotal,
    normalizedPriceScore,
    hybridScore
  };
}

export default function MenuPackagesTab({ menuPackages, activeTimeFilter }) {
  const [sortBy, setSortBy] = useState("strongest");

  const preparedPackages = useMemo(() => {
    const maxOpportunityScore = Math.max(
      ...menuPackages.map((pkg) => Number(pkg.price_opportunity_score || 0)),
      0
    );

    const enriched = menuPackages.map((pkg) => enrichPackage(pkg, maxOpportunityScore));

    if (sortBy === "valuable") {
      return enriched.sort(
        (left, right) =>
          Number(right.price_opportunity_score) - Number(left.price_opportunity_score)
      );
    }

    if (sortBy === "hybrid") {
      return enriched.sort((left, right) => right.hybridScore - left.hybridScore);
    }

    return enriched.sort(
      (left, right) => Number(right.bayes_factor) - Number(left.bayes_factor)
    );
  }, [menuPackages, sortBy]);

  return (
    <div className="tab-stack">
      <SortControls sortBy={sortBy} onChange={setSortBy} />

      {preparedPackages.map((pkg) => {
        const badge = getHabitBadge(Number(pkg.bayes_factor));
        const opportunity = getOpportunityMeta(Number(pkg.price_opportunity_score));

        return (
          <article key={pkg.package_name} className="package-card glass-card">
            {activeTimeFilter ? (
              <div className="context-badge">{TIME_CONTEXT_META[activeTimeFilter]}</div>
            ) : null}

            <div className="package-top">
              <div>
                <h3>{pkg.package_name}</h3>
                {pkg.is_cross_category ? (
                  <span className="mix-badge">{tr.differentCuisines}</span>
                ) : null}
              </div>
              <span className={badge.className}>{badge.label}</span>
            </div>

            <div className="package-items">
              <span>{pkg.items[0]}</span>
              <span className="flow-arrow">→</span>
              <span>{pkg.items[1]}</span>
            </div>

            <CategoryFlow from={pkg.antecedent_category} to={pkg.consequent_category} />

            <p className="package-description">
              <em>{formatPackageDescription(pkg.package_description)}</em>
            </p>

            <section className="price-analysis-box">
              <h4>💰 {tr.priceAnalysisTitle}</h4>
              <p className="price-analysis-note">{tr.realMenuPrices}</p>

              <div className="price-line-items">
                {pkg.itemPrices.map((item) => (
                  <div key={item.name} className="price-line">
                    <span>{item.name}</span>
                    <strong>{formatCurrency(item.price)}</strong>
                  </div>
                ))}
              </div>

              <div className="price-divider" />

              <div className="price-line total-line">
                <span>{tr.menuPrice}</span>
                <strong>{formatCurrency(pkg.verifiedTotal)}</strong>
              </div>

              <PriceStrategyBadge
                packageTotalPrice={pkg.verifiedTotal}
                bayesFactor={Number(pkg.bayes_factor)}
              />

              <div className={opportunity.className}>
                <div className="price-line">
                  <span>
                    {tr.opportunityText.replace(
                      "{amount}",
                      `$${Number(pkg.price_opportunity_score).toFixed(2)}`
                    )}
                  </span>
                </div>
                <small>{opportunity.label}</small>
              </div>
            </section>
          </article>
        );
      })}
    </div>
  );
}
