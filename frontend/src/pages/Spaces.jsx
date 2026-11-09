import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { Empty, ErrorBanner, errorMessage } from "../components/Common.jsx";
import { Dialog } from "./Library.jsx";

export function Spaces({ user }) {
  const [spaces, setSpaces] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    api
      .spaces()
      .then(setSpaces)
      .catch((err) => setError(errorMessage(err)));

  useEffect(() => {
    load();
  }, []);

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Knowledge Spaces</h2>
          <p className="muted">Curated collections of documents for a team or project.</p>
        </div>
        {user.role !== "viewer" && (
          <button className="btn primary" onClick={() => setCreating(true)}>New space</button>
        )}
      </div>
      <ErrorBanner error={error} />
      {spaces.length === 0 ? (
        <Empty>No spaces you can access yet.</Empty>
      ) : (
        <div className="table">
          {spaces.map((s) => (
            <button key={s.space_id} className="row" onClick={() => setActiveId(s.space_id)}>
              <span className="row-title">{s.name}</span>
              <span className="muted">{s.description}</span>
            </button>
          ))}
        </div>
      )}
      {creating && (
        <CreateSpace
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            load();
          }}
        />
      )}
      {activeId && (
        <SpaceDialog
          spaceId={activeId}
          user={user}
          onClose={() => setActiveId(null)}
          onDeleted={() => {
            setActiveId(null);
            load();
          }}
        />
      )}
    </section>
  );
}

function CreateSpace({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", description: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createSpace(form);
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <Dialog title="New space" onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <ErrorBanner error={error} />
        <label>
          Name
          <input required minLength={2} maxLength={80} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          Description
          <textarea maxLength={500} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </label>
        <div className="actions">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={busy}>Create space</button>
        </div>
      </form>
    </Dialog>
  );
}

function SpaceDialog({ spaceId, user, onClose, onDeleted }) {
  const [space, setSpace] = useState(null);
  const [library, setLibrary] = useState([]);
  const [error, setError] = useState("");
  const [pick, setPick] = useState("");

  const load = () =>
    api
      .space(spaceId)
      .then(setSpace)
      .catch((err) => setError(errorMessage(err)));

  useEffect(() => {
    load();
    api.documents().then(setLibrary).catch(() => setLibrary([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spaceId]);

  if (!space) {
    return <Dialog title="Space" onClose={onClose}><ErrorBanner error={error} /></Dialog>;
  }

  const canManage = user.role === "admin" || space.owner_id === user.user_id;
  const inSpace = new Set((space.documents ?? []).map((d) => d.document_id));
  const addable = library.filter((d) => !inSpace.has(d.document_id) && d.status === "processed");

  async function run(action) {
    setError("");
    try {
      await action();
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove() {
    if (!window.confirm(`Delete the space "${space.name}"? Documents are not deleted.`)) return;
    try {
      await api.deleteSpace(space.space_id);
      onDeleted();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Dialog title={space.name} onClose={onClose}>
      <div className="stack">
        <ErrorBanner error={error} />
        {space.description && <p className="muted">{space.description}</p>}
        <div>
          <h4>Documents</h4>
          {(space.documents ?? []).length === 0 ? (
            <p className="muted">No documents in this space yet.</p>
          ) : (
            <ul className="list">
              {space.documents.map((d) => (
                <li key={d.document_id}>
                  <span>{d.title || d.filename}</span>
                  {canManage && (
                    <button className="btn link" onClick={() => run(() => api.removeSpaceDocument(space.space_id, d.document_id))}>
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {canManage && addable.length > 0 && (
            <div className="inline">
              <select value={pick} onChange={(e) => setPick(e.target.value)}>
                <option value="">Add a document...</option>
                {addable.map((d) => (
                  <option key={d.document_id} value={d.document_id}>{d.title || d.filename}</option>
                ))}
              </select>
              <button
                className="btn ghost"
                disabled={!pick}
                onClick={() => run(async () => {
                  await api.addSpaceDocument(space.space_id, pick);
                  setPick("");
                })}
              >
                Add
              </button>
            </div>
          )}
        </div>
        {canManage && (
          <MembersEditor space={space} onSaved={load} onError={setError} />
        )}
        {canManage && (
          <div className="actions">
            <button className="btn danger" onClick={remove}>Delete space</button>
          </div>
        )}
      </div>
    </Dialog>
  );
}

function MembersEditor({ space, onSaved, onError }) {
  const [people, setPeople] = useState([]);
  const [members, setMembers] = useState(space.member_ids ?? []);

  useEffect(() => {
    api.directory().then(setPeople).catch(() => setPeople([]));
  }, []);

  async function save() {
    try {
      await api.setSpaceMembers(space.space_id, members);
      onSaved();
    } catch (err) {
      onError(errorMessage(err));
    }
  }

  return (
    <div>
      <h4>Members</h4>
      <fieldset className="people">
        {people.map((p) => (
          <label key={p.user_id} className="check">
            <input
              type="checkbox"
              checked={members.includes(p.user_id)}
              onChange={(e) =>
                setMembers(e.target.checked ? [...members, p.user_id] : members.filter((id) => id !== p.user_id))
              }
            />
            {p.name}
          </label>
        ))}
      </fieldset>
      <button className="btn ghost" onClick={save}>Save members</button>
    </div>
  );
}
