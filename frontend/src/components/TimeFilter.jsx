import tr from "../i18n";

const TIME_OPTIONS = [
  { label: tr.serviceAll, value: null, icon: "", countLabel: "" },
  { label: tr.serviceLunch, value: "lunch", icon: "☀️", countLabel: tr.lunchCountLabel },
  {
    label: tr.serviceAfternoon,
    value: "afternoon",
    icon: "🌤",
    countLabel: tr.afternoonCountLabel
  },
  { label: tr.serviceDinner, value: "dinner", icon: "🌆", countLabel: tr.dinnerCountLabel },
  {
    label: tr.serviceNight,
    value: "night",
    icon: "🌙",
    countLabel: tr.nightCountLabel,
    warning: true
  }
];

const TIME_HELPER = {
  lunch: tr.lunchInfo,
  afternoon: tr.afternoonInfo,
  dinner: tr.dinnerInfo,
  night: tr.nightInfo
};

export default function TimeFilter({ selectedTimeFilter, onTimeFilterChange }) {
  const helperText = selectedTimeFilter ? TIME_HELPER[selectedTimeFilter] : tr.timeAllInfo;

  return (
    <div className="time-filter">
      <span className="filter-title">⏰ {tr.timeFilterTitle}</span>

      <div className="time-filter-row">
        {TIME_OPTIONS.map((option) => {
          const isActive = selectedTimeFilter === option.value;

          return (
            <button
              key={option.label}
              type="button"
              className={`time-toggle ${isActive ? "time-toggle-active" : ""}`}
              onClick={() => onTimeFilterChange(option.value)}
              title={option.warning ? tr.nightWarning : ""}
            >
              <span className="time-toggle-label">
                {option.icon ? `${option.icon} ${option.label}` : option.label}
                {option.warning ? " ⚠️" : ""}
              </span>
              {option.countLabel ? <small>{option.countLabel}</small> : null}
            </button>
          );
        })}
      </div>

      <p className="category-filter-note">{helperText}</p>
    </div>
  );
}
