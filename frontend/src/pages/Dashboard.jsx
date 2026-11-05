import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { ErrorBanner, Spinner, Stat } from "../components/Common.jsx";

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  const load = () =>
    api
      .status()
      .then((s) => {
        setStatus(s);
        setError("");
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  if (!status && !error) return <Spinner label="Loading status…" />;
  const llm = status?.llm;
  return (
    <section>
      <h2>Dashboard</h2>
      <ErrorBanner message={error} />
      {status && (
        <>
          <div className="stats">
            <Stat label="Documents uploaded" value={status.documents_uploaded} />
            <Stat label="Documents processed" value={status.documents_processed} />
            <Stat label="Chunks indexed" value={status.chunks_indexed} />
            <Stat
              label={`Local LLM (${llm.model})`}
              value={llm.reachable && llm.model_installed ? "Ready" : llm.reachable ? "Model missing" : "Ollama offline"}
              tone={llm.reachable && llm.model_installed ? "ok" : "bad"}
            />
          </div>
          <div className="card">
            <h3>Local models</h3>
            <p>
              Embedding model: <code>{status.embedding_model}</code>{" "}
              <span className="muted">({status.embedding_model_loaded ? "loaded" : "loads on first use"})</span>
            </p>
            {!llm.reachable && <p className="muted">Start Ollama, then run <code>ollama pull {llm.model}</code>.</p>}
            {llm.reachable && !llm.model_installed && <p className="muted">Run <code>ollama pull {llm.model}</code>.</p>}
          </div>
          <button onClick={load}>Refresh</button>
        </>
      )}
    </section>
  );
}
