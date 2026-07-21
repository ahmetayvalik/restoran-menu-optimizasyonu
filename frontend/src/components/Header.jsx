import tr from "../i18n";

function getHealthLabel(healthStatus) {
  if (healthStatus === "connected") {
    return { text: tr.backendConnected, className: "status-badge status-ok" };
  }
  if (healthStatus === "disconnected") {
    return { text: tr.backendDisconnected, className: "status-badge status-error" };
  }
  return { text: tr.backendChecking, className: "status-badge status-pending" };
}

export default function Header({ healthStatus }) {
  const health = getHealthLabel(healthStatus);

  return (
    <header className="hero-panel glass-card">
      <div>
        <span className="eyebrow">{tr.appEyebrow}</span>
        <div className="hero-heading-row">
          <h1>{tr.headerTitle}</h1>
          <span className={health.className}>{health.text}</span>
        </div>
        <p className="hero-text">{tr.headerSubtitle}</p>
      </div>

      <div className="hero-metrics">
        <div className="metric-card">
          <span>{tr.backendLabel}</span>
          <strong>FastAPI :8000</strong>
        </div>
        <div className="metric-card">
          <span>{tr.frontendLabel}</span>
          <strong>React + Vite :5173</strong>
        </div>
      </div>
    </header>
  );
}
