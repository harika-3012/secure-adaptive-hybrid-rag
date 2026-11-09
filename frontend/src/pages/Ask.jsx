import { useEffect, useState } from "react";
import { api } from "../services/api.js";
import { Empty, ErrorBanner, errorMessage } from "../components/Common.jsx";

export function Ask() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    api
      .conversations()
      .then(setConversations)
      .catch((err) => setError(errorMessage(err)));

  useEffect(() => {
    load();
  }, []);

  async function startNew(scope) {
    setError("");
    try {
      const conv = await api.createConversation(scope);
      setCreating(false);
      setActiveId(conv.conversation_id);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(id) {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await api.deleteConversation(id);
      if (activeId === id) setActiveId(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="ask">
      <aside className="history">
        <button className="btn primary wide" onClick={() => setCreating(true)}>New conversation</button>
        <ErrorBanner error={error} />
        {conversations.length === 0 && <p className="muted">No conversations yet.</p>}
        <ul className="list">
          {conversations.map((c) => (
            <li key={c.conversation_id} className={c.conversation_id === activeId ? "selected" : ""}>
              <button className="btn link" onClick={() => setActiveId(c.conversation_id)}>{c.title}</button>
              <button className="btn link" onClick={() => remove(c.conversation_id)} aria-label="Delete conversation">Delete</button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="chat">
        {creating && <ScopePicker onStart={startNew} onCancel={() => setCreating(false)} />}
        {!creating && activeId && <Thread key={activeId} conversationId={activeId} />}
        {!creating && !activeId && <Empty>Start a conversation to ask about your documents.</Empty>}
      </div>
    </section>
  );
}

function ScopePicker({ onStart, onCancel }) {
  const [type, setType] = useState("all");
  const [spaces, setSpaces] = useState([]);
  const [spaceId, setSpaceId] = useState("");

  useEffect(() => {
    api.spaces().then(setSpaces).catch(() => setSpaces([]));
  }, []);

  const scope = type === "space" ? { type, space_id: spaceId } : { type: "all" };

  return (
    <div className="stack scope">
      <h3>Which documents should this conversation use?</h3>
      <label>
        Scope
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="all">All documents I can access</option>
          <option value="space">A knowledge space</option>
        </select>
      </label>
      {type === "space" && (
        <label>
          Space
          <select value={spaceId} onChange={(e) => setSpaceId(e.target.value)}>
            <option value="">Choose a space...</option>
            {spaces.map((s) => <option key={s.space_id} value={s.space_id}>{s.name}</option>)}
          </select>
        </label>
      )}
      <div className="actions">
        <button className="btn ghost" onClick={onCancel}>Cancel</button>
        <button className="btn primary" disabled={type === "space" && !spaceId} onClick={() => onStart(scope)}>
          Start
        </button>
      </div>
    </div>
  );
}

function Thread({ conversationId }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [compare, setCompare] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .conversation(conversationId)
      .then((c) => setMessages(c.messages ?? []))
      .catch((err) => setError(errorMessage(err)));
  }, [conversationId]);

  async function send(e) {
    e.preventDefault();
    const question = draft.trim();
    if (question.length < 2) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.ask(conversationId, question, compare);
      setMessages((m) => [...m, res.user_message, res.assistant_message]);
      setDraft("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="thread">
      <div className="messages">
        {messages.length === 0 && <Empty>Ask a question in plain language.</Empty>}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <p>{m.content}</p>
            {m.role === "assistant" && m.note && <p className="muted">{m.note}</p>}
            {m.role === "assistant" && m.citations?.length > 0 && (
              <ul className="citations">
                {m.citations.map((c) => (
                  <li key={c.label}>
                    <strong>[{c.label}]</strong> {c.document_name}, page {c.page}
                    <span className="muted"> - {c.excerpt}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      <ErrorBanner error={error} />
      <form className="composer" onSubmit={send}>
        <textarea
          rows={2}
          maxLength={2000}
          placeholder="Ask a question about your documents"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <div className="composer-actions">
          <label className="check">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} />
            Compare across documents
          </label>
          <button className="btn primary" disabled={busy || draft.trim().length < 2}>
            {busy ? "Thinking..." : "Ask"}
          </button>
        </div>
      </form>
    </div>
  );
}
