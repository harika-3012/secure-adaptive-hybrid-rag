import { useState } from "react";
import { api, METHODS } from "../services/api.js";
import { AdaptivePanel, ChunkList, ErrorBanner, Spinner } from "../components/Common.jsx";

const pct = (v) => (v == null ? "–" : v.toFixed(3));

function EvaluationPanel() {
  const [ev, setEv] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      setEv(await api.runEvaluation({ k: 5 }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  const loadSaved = async () => {
    setError("");
    try {
      setEv(await api.evaluationResults());
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="card">
      <h3>Preliminary evaluation</h3>
      <p className="muted">
        Runs all four methods over the bundled synthetic question set (isolated from your uploads).
      </p>
      <div className="row">
        <button className="primary" onClick={run} disabled={loading}>
          {loading ? "Running…" : "Run evaluation"}
        </button>
        <button onClick={loadSaved} disabled={loading}>
          Load last results
        </button>
      </div>
      {loading && <Spinner label="Ingesting corpus and running 4 methods × all questions…" />}
      <ErrorBanner message={error} />
      {ev && (
        <>
          <div className="banner warn">
            {ev.status}: {ev.caveat}
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Method</th>
                <th>P@{ev.k}</th>
                <th>R@{ev.k}</th>
                <th>MRR</th>
                <th>NDCG@{ev.k}</th>
                <th>Latency (ms)</th>
              </tr>
            </thead>
            <tbody>
              {ev.overall.map((r) => (
                <tr key={r.method}>
                  <td>{METHODS.find((m) => m.value === r.method)?.label}</td>
                  <td>{pct(r.precision)}</td>
                  <td>{pct(r.recall)}</td>
                  <td>{pct(r.mrr)}</td>
                  <td>{pct(r.ndcg)}</td>
                  <td>{r.latency_mean_ms.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="charts">
            {ev.charts.map((c) => (
              <img key={c} src={`${api.chartUrl(c)}?t=${encodeURIComponent(ev.generated_at)}`} alt={c} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function Compare() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [selected, setSelected] = useState(METHODS.map((m) => m.value));
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const toggle = (v) => setSelected((s) => (s.includes(v) ? s.filter((x) => x !== v) : [...s, v]));

  const run = async (e) => {
    e.preventDefault();
    if (query.trim().length < 2 || selected.length === 0) return;
    setLoading(true);
    setError("");
    setResults({});
    try {
      const out = {};
      for (const m of selected) {
        out[m] = await api.search({ query: query.trim(), method: m, top_k: Number(topK) });
      }
      setResults(out);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <h2>Retrieval comparison</h2>
      <form className="card" onSubmit={run}>
        <input
          className="wide"
          placeholder="Enter a query and compare how each retrieval method ranks the evidence"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="row">
          {METHODS.map((m) => (
            <label key={m.value} className="check">
              <input type="checkbox" checked={selected.includes(m.value)} onChange={() => toggle(m.value)} /> {m.label}
            </label>
          ))}
          <label>
            Top-k <input type="number" min={1} max={20} value={topK} onChange={(e) => setTopK(e.target.value)} />
          </label>
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Searching…" : "Compare"}
          </button>
        </div>
      </form>
      {loading && <Spinner label="Retrieving…" />}
      <ErrorBanner message={error} />

      <div className="columns">
        {selected
          .filter((m) => results[m])
          .map((m) => (
            <div className="card col" key={m}>
              <h3>
                {METHODS.find((x) => x.value === m).label}
                <span className="muted"> · {results[m].latency_ms.toFixed(1)} ms</span>
              </h3>
              {results[m].fixed_alpha != null && <p className="muted">α (BM25 weight) = {results[m].fixed_alpha}</p>}
              <AdaptivePanel adaptive={results[m].adaptive} />
              <ChunkList items={results[m].results} />
            </div>
          ))}
      </div>

      <EvaluationPanel />
    </section>
  );
}
