import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api.js";
import { ErrorBanner } from "../components/Common.jsx";

const ACCEPT = ".pdf,.docx,.txt";

export default function Upload() {
  const [docs, setDocs] = useState([]);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const refresh = useCallback(
    () =>
      api
        .listDocuments()
        .then(setDocs)
        .catch((e) => setError(e.message)),
    []
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any document is still being processed.
  const pending = docs.some((d) => d.status === "queued" || d.status === "processing");
  useEffect(() => {
    if (!pending) return undefined;
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, [pending, refresh]);

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await api.uploadDocument(file);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (d) => {
    if (!window.confirm(`Delete ${d.filename}?`)) return;
    try {
      await api.deleteDocument(d.document_id);
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <section>
      <h2>Documents</h2>
      <div className="card row">
        <input ref={inputRef} type="file" accept={ACCEPT} onChange={(e) => setFile(e.target.files[0] || null)} />
        <button className="primary" onClick={upload} disabled={!file || busy}>
          {busy ? "Uploading…" : "Upload"}
        </button>
        <span className="muted">PDF, DOCX or TXT</span>
      </div>
      <ErrorBanner message={error} />
      <table className="table">
        <thead>
          <tr>
            <th>File</th>
            <th>Status</th>
            <th>Pages</th>
            <th>Chunks</th>
            <th>Size</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {docs.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                No documents yet.
              </td>
            </tr>
          )}
          {docs.map((d) => (
            <tr key={d.document_id}>
              <td>
                {d.filename}
                {d.synthetic && <span className="pill">synthetic</span>}
                {d.error && <div className="err-text">{d.error}</div>}
              </td>
              <td>
                <span className={`pill status-${d.status}`}>{d.status}</span>
              </td>
              <td>{d.pages || "–"}</td>
              <td>{d.chunks || "–"}</td>
              <td>{(d.size_bytes / 1024).toFixed(1)} KB</td>
              <td>
                <button onClick={() => remove(d)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
