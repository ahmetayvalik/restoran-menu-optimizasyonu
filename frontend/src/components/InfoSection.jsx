import tr from "../i18n";

export default function InfoSection() {
  return (
    <section className="info-layout">
      <article className="info-card glass-card">
        <span className="eyebrow">{tr.howItWorks}</span>
        <h3>{tr.analysisFlow}</h3>
        <ul className="info-list">
          <li>{tr.flowUpload}</li>
          <li>{tr.flowBasket}</li>
          <li>{tr.flowPatterns}</li>
          <li>{tr.flowSuggestions}</li>
        </ul>
      </article>

      <article className="info-card glass-card">
        <span className="eyebrow">{tr.managerNotes}</span>
        <h3>{tr.methodFrame}</h3>
        <ul className="info-list">
          <li>{tr.noteNotSupervised}</li>
          <li>{tr.notePattern}</li>
          <li>{tr.noteAction}</li>
        </ul>
      </article>

      <article className="info-card glass-card">
        <span className="eyebrow">{tr.demoNote}</span>
        <h3>{tr.businessValue}</h3>
        <p className="section-copy">{tr.businessValueText}</p>
      </article>
    </section>
  );
}
