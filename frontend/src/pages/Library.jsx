import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { Badge, Empty, ErrorBanner, errorMessage } from "../components/Common.jsx";

const VISIBILITY_LABELS = {
  private: "Only me and administrators",
  shared: "Selected people",
  organization: "Everyone in the organization",
};

export function Library({ user }) {
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [showUpload, setShowUpload] = useState(false);

  const load = () =>
    api
      .documents()
      .then(setDocs)
      .catch((err) => setError(errorMessage(err)));

  useEffect(() => {
    load();
  }, []);

  const hasPending = docs.some((d) => d.status !== "processed" && d.status !== "failed");
  useEffect(() => {
    if (!hasPending) return undefined;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [hasPending]);

  async function remove(doc) {
    if (!window.confirm(`Delete "${doc.title || doc.filename}"? This cannot be undone.`)) return;
    try {
      await api.deleteDocument(doc.document_id);
      setSelected(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Documents</h2>
          <p className="muted">Documents you can see. Ask questions about them on the Ask page.</p>
        </div>
        {user.role !== "viewer" && (
          <button className="btn primary" onClick={() => setShowUpload(true)}>Upload document</button>
        )}
      </div>
      <ErrorBanner error={error} />
      {docs.length === 0 ? (
        <Empty>No documents yet.</Empty>
      ) : (
        <div className="table">
          {docs.map((d) => (
            <button key={d.document_id} className="row" onClick={() => setSelected(d)}>
              <span className="row-title">{d.title || d.filename}</span>
              <span className="muted">{d.doc_type}</span>
              <span className="muted">{d.owner_name}</span>
              <Badge tone={d.status === "processed" ? "ok" : d.status === "failed" ? "error" : "neutral"}>
                {d.status}
              </Badge>
            </button>
          ))}
        </div>
      )}
      {showUpload && (
        <UploadDialog
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            load();
          }}
        />
      )}
      {selected && (
        <DocumentDialog
          doc={selected}
          onClose={() => setSelected(null)}
          onChanged={() => {
            load();
          }}
          onDelete={() => remove(selected)}
        />
      )}
    </section>
  );
}

function UploadDialog({ onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [visibility, setVisibility] = useState("private");
  const [people, setPeople] = useState([]);
  const [sharedWith, setSharedWith] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.directory().then(setPeople).catch(() => setPeople([]));
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (!file) return setError("Choose a file to upload.");
    setBusy(true);
    setError("");
    try {
      await api.upload(file, visibility, visibility === "shared" ? sharedWith : []);
      onUploaded();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <Dialog title="Upload document" onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <ErrorBanner error={error} />
        <label>
          File (PDF, DOCX or TXT)
          <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files[0] ?? null)} />
        </label>
        <label>
          Who can see it
          <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
            {Object.entries(VISIBILITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        {visibility === "shared" && (
          <fieldset className="people">
            <legend>Share with</legend>
            {people.map((p) => (
              <label key={p.user_id} className="check">
                <input
                  type="checkbox"
                  checked={sharedWith.includes(p.user_id)}
                  onChange={(e) =>
                    setSharedWith(
                      e.target.checked ? [...sharedWith, p.user_id] : sharedWith.filter((id) => id !== p.user_id)
                    )
                  }
                />
                {p.name}
              </label>
            ))}
          </fieldset>
        )}
        <div className="actions">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={busy}>{busy ? "Uploading..." : "Upload"}</button>
        </div>
      </form>
    </Dialog>
  );
}

function DocumentDialog({ doc, onClose, onDelete, onChanged }) {
  const [summary, setSummary] = useState(doc.summary ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function summarize(refresh) {
    setBusy(true);
    setError("");
    try {
      const res = await api.summarize(doc.document_id, refresh);
      setSummary(res.summary);
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog title={doc.title || doc.filename} onClose={onClose}>
      <div className="stack">
        <ErrorBanner error={error} />
        <dl className="facts">
          <dt>Type</dt><dd>{doc.doc_type}</dd>
          <dt>Owner</dt><dd>{doc.owner_name}</dd>
          <dt>Access</dt><dd>{VISIBILITY_LABELS[doc.visibility] ?? doc.visibility}</dd>
          <dt>Identifiers</dt><dd>{doc.identifiers.join(", ") || "None found"}</dd>
          <dt>Dates</dt><dd>{doc.dates.join(", ") || "None found"}</dd>
          <dt>Keywords</dt><dd>{doc.keywords.join(", ") || "None found"}</dd>
        </dl>
        {doc.key_points.length > 0 && (
          <div>
            <h4>Key points</h4>
            <ul>{doc.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
          </div>
        )}
        <div>
          <h4>Summary</h4>
          {summary ? <p className="summary">{summary}</p> : <p className="muted">No summary yet.</p>}
          {doc.status === "processed" && (
            <button className="btn ghost" disabled={busy} onClick={() => summarize(Boolean(summary))}>
              {busy ? "Summarizing..." : summary ? "Regenerate summary" : "Generate summary"}
            </button>
          )}
        </div>
        {doc.can_manage && (
          <div className="actions">
            <button className="btn danger" onClick={onDelete}>Delete document</button>
          </div>
        )}
      </div>
    </Dialog>
  );
}

export function Dialog({ title, onClose, children }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="dialog" role="dialog" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <h3>{title}</h3>
          <button className="btn ghost" onClick={onClose} aria-label="Close">Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}
