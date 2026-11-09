import { useState } from "react";
import { api } from "../services/api.js";
import { Empty, ErrorBanner, errorMessage } from "../components/Common.jsx";

export function Search() {
  const [query, setQuery] = useState("");
  const [groups, setGroups] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 2) return setError("Enter at least two characters.");
    setBusy(true);
    setError("");
    try {
      const res = await api.search(q);
      setGroups(res.results ?? []);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Search</h2>
          <p className="muted">Find passages across the documents you can access.</p>
        </div>
      </div>
      <form className="searchbar" onSubmit={submit}>
        <input
          type="search"
          placeholder="Describe what you are looking for"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="btn primary" disabled={busy}>{busy ? "Searching..." : "Search"}</button>
      </form>
      <ErrorBanner error={error} />
      {groups && groups.length === 0 && <Empty>No matching passages.</Empty>}
      {groups?.map((g) => (
        <article key={g.document_id} className="result">
          <h3>{g.document_name}</h3>
          {g.passages.map((p) => (
            <blockquote key={p.chunk_id}>
              <span className="muted">Page {p.page}</span>
              <p>{p.excerpt}</p>
            </blockquote>
          ))}
        </article>
      ))}
    </section>
  );
}
