import { useEffect, useState } from "react";
import { api, session } from "../services/api.js";
import { ErrorBanner, errorMessage } from "../components/Common.jsx";

export function Auth({ onSignedIn }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", name: "", password: "" });
  const [setup, setSetup] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.setupStatus().then(setSetup).catch(() => setSetup({ needs_admin: false, self_registration: false }));
  }, []);

  const canRegister = setup?.needs_admin || setup?.self_registration;

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data =
        mode === "login"
          ? await api.login({ email: form.email, password: form.password })
          : await api.register({ email: form.email, name: form.name, password: form.password });
      session.set(data.access_token);
      onSignedIn(data.user);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <h1>{mode === "login" ? "Sign in" : "Create account"}</h1>
        <p className="muted">
          {setup?.needs_admin
            ? "No accounts exist yet. The first account becomes the administrator."
            : "Access your organization's documents and ask questions about them."}
        </p>
        <ErrorBanner error={error} />
        <label>
          Email
          <input type="email" required value={form.email} onChange={update("email")} autoComplete="email" />
        </label>
        {mode === "register" && (
          <label>
            Full name
            <input required minLength={2} value={form.name} onChange={update("name")} autoComplete="name" />
          </label>
        )}
        <label>
          Password
          <input
            type="password"
            required
            minLength={mode === "register" ? 8 : 1}
            value={form.password}
            onChange={update("password")}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </label>
        <button className="btn primary wide" disabled={busy}>
          {busy ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
        {canRegister && (
          <button
            type="button"
            className="btn link"
            onClick={() => {
              setError("");
              setMode(mode === "login" ? "register" : "login");
            }}
          >
            {mode === "login" ? "Create an account" : "Already have an account? Sign in"}
          </button>
        )}
      </form>
    </div>
  );
}
