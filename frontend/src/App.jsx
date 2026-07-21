import { useEffect, useMemo, useState } from "react";
import AnalysisSummaryBanner from "./components/AnalysisSummaryBanner";
import BaselineComparisonTab from "./components/BaselineComparisonTab";
import BayesAnalysisTab from "./components/BayesAnalysisTab";
import ErrorAlert from "./components/ErrorAlert";
import MenuPackagesTab from "./components/MenuPackagesTab";
import TrendTab from "./components/TrendTab";
import UploadPanel from "./components/UploadPanel";
import tr from "./i18n";

const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const ANALYZE_URL = `${BACKEND_URL}/upload-and-analyze`;
const HEALTH_URL = `${BACKEND_URL}/health`;

function getHealthLabel(healthStatus) {
  if (healthStatus === "connected") {
    return { text: tr.backendConnected, className: "status-badge status-ok" };
  }
  if (healthStatus === "disconnected") {
    return { text: tr.backendDisconnected, className: "status-badge status-error" };
  }
  return { text: tr.backendChecking, className: "status-badge status-pending" };
}

function mapErrorMessage(message) {
  if (!message) {
    return tr.errorGeneric;
  }

  const lower = message.toLowerCase();
  if (lower.includes("failed to fetch") || lower.includes("networkerror") || lower.includes("load failed")) {
    return tr.errorBackendDown;
  }
  if (lower.includes("order_id ve item_name")) {
    return tr.errorMissingColumn;
  }
  if (lower.includes("anlamli capraz satis kombinasyonu bulunamadi")) {
    return tr.errorNoRules;
  }
  if (lower.includes("csv formatinda") || lower.includes("csv")) {
    return tr.errorCsv;
  }
  if (lower.includes("yeterli siparis yok")) {
    return tr.errorInsufficientData;
  }

  return message;
}

function EmptyState({ title, message, eyebrow = tr.resultArea }) {
  return (
    <div className="empty-state glass-card">
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{message}</p>
    </div>
  );
}

function TabNavigation({ activeTab, onChange }) {
  const tabs = [
    { id: "packages", label: tr.tabMenuPackages },
    { id: "bayes", label: tr.tabHabits },
    { id: "baseline", label: tr.tabWhyThisSystem },
    { id: "trend", label: tr.tabMonthlyChange },
  ];

  return (
    <div className="tab-nav">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`tab-button ${activeTab === tab.id ? "tab-button-active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function TabContent({ activeTab, data }) {
  if (activeTab === "bayes") {
    return <BayesAnalysisTab bayesRules={data.bayes_rules} />;
  }
  if (activeTab === "baseline") {
    return <BaselineComparisonTab baselineComparison={data.baseline_comparison} />;
  }
  if (activeTab === "trend") {
    return <TrendTab monthlyTrend={data.monthly_trend} />;
  }
  return (
    <MenuPackagesTab
      menuPackages={data.menu_packages}
      activeTimeFilter={data.analysis_summary?.active_time_filter || null}
    />
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [viewState, setViewState] = useState("idle");
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [healthStatus, setHealthStatus] = useState("checking");
  const [activeTab, setActiveTab] = useState("packages");
  const [categoryFilter, setCategoryFilter] = useState(null);
  const [timeFilter, setTimeFilter] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function checkBackend() {
      try {
        const response = await fetch(HEALTH_URL);
        if (!response.ok) {
          throw new Error("Health endpoint hata verdi.");
        }
        const payload = await response.json();
        if (mounted) {
          setHealthStatus(payload.status === "ok" ? "connected" : "disconnected");
        }
      } catch {
        if (mounted) {
          setHealthStatus("disconnected");
        }
      }
    }

    checkBackend();
    return () => {
      mounted = false;
    };
  }, []);

  const health = getHealthLabel(healthStatus);
  const placeholderMessage = useMemo(
    () => (viewState === "empty" ? tr.emptyMessage : tr.placeholderMessage),
    [viewState]
  );

  const handleAnalyze = async () => {
    if (!file) {
      setError(tr.errorPickFile);
      setData(null);
      setViewState("error");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setViewState("loading");
    setError("");
    setData(null);
    setActiveTab("packages");

    try {
      const params = new URLSearchParams();
      if (categoryFilter) {
        params.set("category_filter", categoryFilter);
      }
      if (timeFilter) {
        params.set("time_filter", timeFilter);
      }

      const query = params.toString() ? `?${params.toString()}` : "";
      const response = await fetch(`${ANALYZE_URL}${query}`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok || payload.status === "error") {
        throw new Error(payload.message || tr.errorGeneric);
      }

      if (!payload.menu_packages?.length && !payload.bayes_rules?.length) {
        setViewState("empty");
        setData(payload);
        return;
      }

      setData(payload);
      setViewState("success");
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message));
      setViewState("error");
    }
  };

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="page">
        <section className="hero-panel glass-card hero-panel-single">
          <div className="hero-copy">
            <span className="eyebrow">{tr.appEyebrow}</span>
            <div className="hero-heading-row">
              <div>
                <h1>{tr.appTitle}</h1>
                <p className="hero-text">{tr.appSubtitle}</p>
              </div>
              <span className={health.className}>{health.text}</span>
            </div>
          </div>

          <UploadPanel
            file={file}
            loading={viewState === "loading"}
            onFileChange={setFile}
            onAnalyze={handleAnalyze}
            selectedCategory={categoryFilter}
            onCategoryChange={setCategoryFilter}
            selectedTimeFilter={timeFilter}
            onTimeFilterChange={setTimeFilter}
          />
        </section>

        {error ? <ErrorAlert message={error} /> : null}
        {data?.analysis_summary ? <AnalysisSummaryBanner summary={data.analysis_summary} /> : null}

        {viewState === "loading" ? (
          <section className="results-section">
            <EmptyState eyebrow={tr.analysisEyebrow} title={tr.loadingTitle} message={tr.loadingMessage} />
          </section>
        ) : null}

        {viewState === "empty" ? (
          <section className="results-section">
            <EmptyState eyebrow={tr.noResult} title={tr.noDisplayableResult} message={placeholderMessage} />
          </section>
        ) : null}

        {viewState === "idle" ? (
          <section className="results-section">
            <EmptyState title={tr.waitingTitle} message={placeholderMessage} />
          </section>
        ) : null}

        {viewState === "success" && data ? (
          <section className="tabs-section">
            <TabNavigation activeTab={activeTab} onChange={setActiveTab} />
            <TabContent activeTab={activeTab} data={data} />
          </section>
        ) : null}
      </main>
    </div>
  );
}
