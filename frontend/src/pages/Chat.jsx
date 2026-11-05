import { useState } from "react";
import { api, METHODS } from "../services/api.js";
import { AdaptivePanel, ChunkList, ErrorBanner, MethodSelect, Spinner } from "../components/Common.jsx";

export default function Chat() {
  const [question, setQuestion] = useState("");
  const [method, setMethod] = useState("adaptive_hybrid");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resp, setResp] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (question.trim().length < 2) return;
    setLoading(true);
    setError("");
    setResp(null);
    try {
      setResp(await api.chat({ query: question.trim(), method, top_k: Number(topK) }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const cited = resp ? new Set(resp.citations.filter((c) => c.cited_by_model).map((c) => c.label)) : null;

  return (
    <section>
      <h2>Ask your documents</h2>
      <form className="card" onSubmit={submit}>
        <textarea
          rows={3}
          placeholder="e.g. What does POL-SEC-007 require?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <div className="row">
          <label>
            Retrieval <MethodSelect value={method} onChange={setMethod} methods={METHODS} />
          </label>
          <label>
            Top-k{" "}
            <input type="number" min={1} max={20} value={topK} onChange={(e) => setTopK(e.target.value)} />
          </label>
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Working…" : "Ask"}
          </button>
        </div>
      </form>

      {loading && <Spinner label="Retrieving evidence and generating an answer with the local model…" />}
      <ErrorBanner message={error} />

      {resp && (
        <>
          <div className={`card answer ${resp.sufficient_evidence ? "" : "insufficient"}`}>
            <h3>Answer</h3>
            <p className="answer-text">{resp.answer}</p>
            <div className="muted">
              {resp.model} · retrieval {resp.retrieval_latency_ms.toFixed(0)} ms · generation{" "}
              {resp.generation_latency_ms.toFixed(0)} ms · method {resp.method.replace("_", " ")}
            </div>
          </div>
          <AdaptivePanel adaptive={resp.adaptive} />
          <div className="card">
            <h3>Sources</h3>
            <p className="muted">
              Retrieved evidence passages. “cited” marks passages the model referenced; uncited passages were
              supplied as context only.
            </p>
            <ChunkList items={resp.retrieved} citedLabels={cited} />
          </div>
        </>
      )}
    </section>
  );
}
