import tr from "../i18n";

function formatCurrency(value) {
  return `$${Number(value).toFixed(2)}`;
}

function getStrategyMeta(packageTotalPrice, bayesFactor) {
  if (bayesFactor > 1.5) {
    return {
      className: "strategy-badge strategy-badge-strong",
      title: tr.strategyApply,
      price: formatCurrency(packageTotalPrice),
      detail: tr.strategyApplyDesc
    };
  }

  if (bayesFactor >= 1.2) {
    return {
      className: "strategy-badge strategy-badge-medium",
      title: tr.strategyDiscount,
      price: formatCurrency(packageTotalPrice * 0.9),
      detail: tr.strategyDiscountDesc.replace("{price}", formatCurrency(packageTotalPrice * 0.92))
    };
  }

  return {
    className: "strategy-badge strategy-badge-soft",
    title: tr.strategyTry,
    price: tr.strategyTryPrice,
    detail: tr.strategyTryDesc
  };
}

export default function PriceStrategyBadge({ packageTotalPrice, bayesFactor }) {
  const meta = getStrategyMeta(packageTotalPrice, bayesFactor);

  return (
    <div className={meta.className}>
      <span>{meta.title}</span>
      <strong>{meta.price}</strong>
      <small>{meta.detail}</small>
      <p />
    </div>
  );
}
