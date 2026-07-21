import { useId, useState } from "react";
import tr from "../i18n";

function getRelationStrength(lift) {
  if (lift > 2) {
    return tr.explanationStrong;
  }
  if (lift >= 1.5) {
    return tr.explanationMedium;
  }
  return tr.explanationWeak;
}

function normalizePercentage(value) {
  return Math.round(Number(value) * 100);
}

function normalizeConfidence(rule) {
  if (rule.confidence !== undefined && rule.confidence !== null) {
    return Number(rule.confidence);
  }
  if (rule.guven_orani_yuzde !== undefined && rule.guven_orani_yuzde !== null) {
    return Number(rule.guven_orani_yuzde) / 100;
  }
  return 0;
}

function normalizeSupport(rule) {
  return rule.support !== undefined && rule.support !== null ? Number(rule.support) : 0;
}

function normalizeLift(rule) {
  return rule.lift !== undefined && rule.lift !== null
    ? Number(rule.lift)
    : Number(rule.satis_artirma_carpani || 0);
}

function normalizeAntecedent(rule) {
  if (rule.antecedent) {
    return rule.antecedent;
  }
  if (Array.isArray(rule.ana_urunler)) {
    return rule.ana_urunler.join(", ");
  }
  return "";
}

function normalizeConsequent(rule) {
  if (rule.consequent) {
    return rule.consequent;
  }
  if (Array.isArray(rule.yaninda_satilacak_urun)) {
    return rule.yaninda_satilacak_urun.join(", ");
  }
  return "";
}

export default function RuleExplanation({ rule }) {
  const [isOpen, setIsOpen] = useState(false);
  const contentId = useId();

  const antecedent = normalizeAntecedent(rule);
  const consequent = normalizeConsequent(rule);
  const confidence = normalizeConfidence(rule);
  const support = normalizeSupport(rule);
  const lift = normalizeLift(rule);
  const strength = getRelationStrength(lift);

  return (
    <div className={`rule-explanation ${isOpen ? "is-open" : ""}`}>
      <button
        type="button"
        className="explanation-toggle"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
        aria-controls={contentId}
      >
        <span>{tr.explanationToggle}</span>
        <span className="explanation-icon">{isOpen ? "-" : "+"}</span>
      </button>

      <div id={contentId} className="explanation-panel" aria-hidden={!isOpen}>
        <div className="explanation-content">
          <p>{tr.explanationBoth.replace("{pct}", String(normalizePercentage(support)))}</p>
          <p>
            {tr.explanationAlso
              .replace("{antecedent}", antecedent)
              .replace("{pct}", String(normalizePercentage(confidence)))
              .replace("{consequent}", consequent)}
          </p>
          <p>
            {tr.explanationStrength
              .replace("{factor}", lift.toFixed(1))
              .replace("{strength}", strength)}
          </p>
        </div>
      </div>
    </div>
  );
}
