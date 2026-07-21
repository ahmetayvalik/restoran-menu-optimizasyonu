import LoadingSpinner from "./LoadingSpinner";
import CategoryFilter from "./CategoryFilter";
import TimeFilter from "./TimeFilter";
import tr from "../i18n";

export default function UploadPanel({
  file,
  loading,
  onFileChange,
  onAnalyze,
  selectedCategory,
  onCategoryChange,
  selectedTimeFilter,
  onTimeFilterChange
}) {
  return (
    <section className="upload-card glass-card">
      <span className="eyebrow">{tr.uploadEyebrow}</span>
      <h2>{tr.uploadTitle}</h2>
      <p className="section-copy">
        {tr.uploadRequirement.replace("{order}", "order_id").replace("{item}", "item_name")}
      </p>

      <label className="upload-dropzone">
        <input
          type="file"
          accept=".csv"
          onChange={(event) => onFileChange(event.target.files?.[0] || null)}
        />
        <span className="upload-label">
          {file ? file.name : tr.uploadSelect}
        </span>
        <span className="upload-hint">{tr.uploadHint}</span>
      </label>

      <CategoryFilter
        selectedCategory={selectedCategory}
        onCategoryChange={onCategoryChange}
      />

      <TimeFilter
        selectedTimeFilter={selectedTimeFilter}
        onTimeFilterChange={onTimeFilterChange}
      />

      <button className="primary-button" onClick={onAnalyze} disabled={loading}>
        {loading ? (
          <>
            <LoadingSpinner />
            {tr.analyzing}
          </>
        ) : (
          tr.analyze
        )}
      </button>
    </section>
  );
}
