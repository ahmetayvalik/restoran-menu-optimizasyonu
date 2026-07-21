import tr from "../i18n";

export default function ErrorAlert({ message }) {
  return (
    <section className="error-alert">
      <strong>{tr.errorTitle}</strong>
      <p>{message}</p>
    </section>
  );
}
