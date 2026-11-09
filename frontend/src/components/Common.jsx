export function ErrorBanner({ error }) {
  if (!error) return null;
  return <div className="alert" role="alert">{error}</div>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function Badge({ tone = "neutral", children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function errorMessage(err) {
  return err?.message || "Something went wrong. Please try again.";
}
