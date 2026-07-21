import { CATEGORY_COLORS, getCategoryColor } from "../constants/categoryColors";
import tr from "../i18n";

const OPTIONS = [
  { label: tr.serviceAll, value: null, icon: "" },
  { label: "Asian", value: "Asian", icon: "\u{1F962}" },
  { label: "Italian", value: "Italian", icon: "\u{1F35D}" },
  { label: "Mexican", value: "Mexican", icon: "\u{1F32E}" },
  { label: "American", value: "American", icon: "\u{1F354}" }
];

export default function CategoryFilter({ selectedCategory, onCategoryChange }) {
  const helperText = selectedCategory
    ? tr.categoryFilterInfo.replace("{category}", selectedCategory)
    : tr.categoryFilterAll;

  return (
    <div className="category-filter">
      <span className="filter-title">{"\u{1F35C}"} {tr.categoryFilterTitle}</span>

      <div className="category-filter-row">
        {OPTIONS.map((option) => {
          const isActive = selectedCategory === option.value;
          const color = option.value ? getCategoryColor(option.value) : CATEGORY_COLORS.null;

          return (
            <button
              key={option.label}
              type="button"
              className={`category-toggle ${isActive ? "category-toggle-active" : ""}`}
              style={{
                borderColor: color,
                backgroundColor: isActive ? color : "rgba(255,255,255,0.45)",
                color: isActive ? "#fff" : "#1f2933"
              }}
              onClick={() => onCategoryChange(option.value)}
            >
              {option.icon ? `${option.icon} ${option.label}` : option.label}
            </button>
          );
        })}
      </div>

      <p className="category-filter-note">{helperText}</p>
    </div>
  );
}
