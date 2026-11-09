import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { Badge, Empty, ErrorBanner, errorMessage } from "../components/Common.jsx";
import { Dialog } from "./Library.jsx";

const TABS = [
  { id: "users", label: "Users" },
  { id: "audit", label: "Audit trail" },
  { id: "system", label: "System" },
];

export function Admin({ user }) {
  const [tab, setTab] = useState("users");
  if (user.role !== "admin") return <Empty>Administrators only.</Empty>;
  return (
    <section>
      <div className="page-head">
        <h2>Administration</h2>
      </div>
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "users" && <UsersPanel currentUser={user} />}
      {tab === "audit" && <AuditPanel />}
      {tab === "system" && <SystemPanel />}
    </section>
  );
}

function UsersPanel({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = () =>
    api
      .users()
      .then(setUsers)
      .catch((err) => setError(errorMessage(err)));

  useEffect(() => {
    load();
  }, []);

  async function update(id, data) {
    setError("");
    try {
      await api.updateUser(id, data);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="stack">
      <div className="actions">
        <button className="btn primary" onClick={() => setCreating(true)}>Add user</button>
      </div>
      <ErrorBanner error={error} />
      <div className="table">
        {users.map((u) => (
          <div key={u.user_id} className="row static">
            <span className="row-title">{u.name} <span className="muted">{u.email}</span></span>
            <select value={u.role} disabled={u.user_id === currentUser.user_id} onChange={(e) => update(u.user_id, { role: e.target.value })}>
              <option value="admin">Administrator</option>
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
            </select>
            <Badge tone={u.active ? "ok" : "error"}>{u.active ? "Active" : "Disabled"}</Badge>
            <button
              className="btn link"
              disabled={u.user_id === currentUser.user_id}
              onClick={() => update(u.user_id, { active: !u.active })}
            >
              {u.active ? "Disable" : "Enable"}
            </button>
          </div>
        ))}
      </div>
      {creating && (
        <Dialog title="Add user" onClose={() => setCreating(false)}>
          <CreateUser onCreated={() => { setCreating(false); load(); }} />
        </Dialog>
      )}
    </div>
  );
}

function CreateUser({ onCreated }) {
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "viewer" });
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createUser(form);
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <form className="stack" onSubmit={submit}>
      <ErrorBanner error={error} />
      <label>Email<input type="email" required value={form.email} onChange={set("email")} /></label>
      <label>Full name<input required minLength={2} value={form.name} onChange={set("name")} /></label>
      <label>Temporary password<input type="password" required minLength={8} value={form.password} onChange={set("password")} /></label>
      <label>
        Role
        <select value={form.role} onChange={set("role")}>
          <option value="viewer">Viewer</option>
          <option value="editor">Editor</option>
          <option value="admin">Administrator</option>
        </select>
      </label>
      <div className="actions"><button className="btn primary">Create user</button></div>
    </form>
  );
}

function AuditPanel() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .audit("?limit=200")
      .then(setRows)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  return (
    <div className="stack">
      <ErrorBanner error={error} />
      {rows.length === 0 && !error && <Empty>No activity recorded yet.</Empty>}
      <div className="table">
        {rows.map((r) => (
          <div key={r.event_id} className="row static">
            <span className="muted">{r.at}</span>
            <span>{r.action}</span>
            <span className="muted">{r.actor_email || r.actor_id || "system"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SystemPanel() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .system()
      .then(setInfo)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  return (
    <div className="stack">
      <ErrorBanner error={error} />
      {info && (
        <dl className="facts">
          {Object.entries(info).map(([key, value]) => (
            <div key={key} className="fact">
              <dt>{key.replace(/_/g, " ")}</dt>
              <dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
