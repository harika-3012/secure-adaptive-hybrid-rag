export function ErrorBanner({ message }) {
  return message ? (
    <div className="banner error" role="alert">
      {message}
    </div>
  ) : null;
}

export function Spinner({ label }) {
  return (
    <div className="spinner-row" role="status">
      <span className="spinner" /> {label}
    </div>
  );
}

export function Stat({ label, value, tone }) {
  return (
    <div className="stat">
      <div className="stat-value" data-tone={tone}>
        {value}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

/** Adaptive-retrieval decision: class, weights and the reasons behind them. */
export function AdaptivePanel({ adaptive }) {
  if (!adaptive) return null;
  const pct = Math.round(adaptive.bm25_weight * 100);
  return (
    <div className="card adaptive">
      <h3>
        Adaptive decision: <span className="pill">{adaptive.query_class.replace("_", " ")}</span>
      </h3>
      <div className="weightbar" aria-label={`BM25 ${pct}%, dense ${100 - pct}%`}>
        <div className="w-bm25" style={{ width: `${pct}%` }}>
          BM25 {adaptive.bm25_weight.toFixed(2)}
        </div>
        <div className="w-dense" style={{ width: `${100 - pct}%` }}>
          Dense {adaptive.dense_weight.toFixed(2)}
        </div>
      </div>
      <ul className="reasons">
        {adaptive.reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    </div>
  );
}

/** Retrieved chunks with expandable evidence. `highlight` marks labels the model cited. */
export function ChunkList({ items, citedLabels = null }) {
  return (
    <div className="chunks">
      {items.map((r) => (
        <details key={r.chunk.chunk_id} className="chunk">
          <summary>
            <span className="rank">S{r.rank}</span>
            <span className="docname">{r.chunk.document_name}</span>
            <span className="muted">p.{r.chunk.page}</span>
            <span className="score">score {r.score.toFixed(3)}</span>
            {citedLabels && citedLabels.has(`S${r.rank}`) && <span className="pill ok">cited</span>}
          </summary>
          <div className="chunk-meta">
            chunk <code>{r.chunk.chunk_id}</code>
            {r.bm25_score != null && <> · BM25(norm) {r.bm25_score.toFixed(3)}</>}
            {r.dense_score != null && <> · dense(norm) {r.dense_score.toFixed(3)}</>}
          </div>
          <p className="excerpt">{r.chunk.text}</p>
        </details>
      ))}
    </div>
  );
}

export function MethodSelect({ value, onChange, methods }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {methods.map((m) => (
        <option key={m.value} value={m.value}>
          {m.label}
        </option>
      ))}
    </select>
  );
}
