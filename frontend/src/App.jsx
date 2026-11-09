import { useCallback, useEffect, useState } from "react";
import { api, session } from "./services/api.js";
import { Auth } from "./pages/Auth.jsx";
import { Library } from "./pages/Library.jsx";
import { Spaces } from "./pages/Spaces.jsx";
import { Ask } from "./pages/Ask.jsx";
import { Search } from "./pages/Search.jsx";
import { Admin } from "./pages/Admin.jsx";

const NAV = [
  { id: "ask", label: "Ask", component: Ask },
  { id: "search", label: "Search", component: Search },
  { id: "library", label: "Documents", component: Library },
  { id: "spaces", label: "Spaces", component: Spaces },
  { id: "admin", label: "Administration", component: Admin, adminOnly: true },
];

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(session.get()));
  const [page, setPage] = useState("ask");

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* the local session is cleared regardless */
    }
    session.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    const expired = () => setUser(null);
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);

  useEffect(() => {
    if (!session.get()) return;
    api
      .me()
      .then(setUser)
      .catch(() => session.clear())
      .finally(() => setChecking(false));
  }, []);

  if (checking) return <div className="boot">Loading...</div>;
  if (!user) return <Auth onSignedIn={setUser} />;

  const visible = NAV.filter((item) => !item.adminOnly || user.role === "admin");
  const current = visible.find((item) => item.id === page) ?? visible[0];
  const Page = current.component;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">Knowledge Assistant</div>
        <nav className="nav">
          {visible.map((item) => (
            <button
              key={item.id}
              className={item.id === current.id ? "nav-item active" : "nav-item"}
              onClick={() => setPage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="account">
          <span className="account-name">{user.name}</span>
          <span className="pill">{user.role}</span>
          <button className="btn ghost" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <main className="content">
        <Page user={user} />
      </main>
    </div>
  );
}
