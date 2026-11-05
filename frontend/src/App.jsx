import { useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import Upload from "./pages/Upload.jsx";
import Chat from "./pages/Chat.jsx";
import Compare from "./pages/Compare.jsx";

const PAGES = [
  { id: "dashboard", label: "Dashboard", component: Dashboard },
  { id: "upload", label: "Documents", component: Upload },
  { id: "chat", label: "Ask", component: Chat },
  { id: "compare", label: "Retrieval comparison", component: Compare },
];

export default function App() {
  const [page, setPage] = useState("dashboard");
  const Page = PAGES.find((p) => p.id === page).component;
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <strong>Secure Adaptive Hybrid RAG</strong>
          <span>Air-gapped enterprise document intelligence · Review 2 prototype</span>
        </div>
        <nav>
          {PAGES.map((p) => (
            <button key={p.id} className={p.id === page ? "tab active" : "tab"} onClick={() => setPage(p.id)}>
              {p.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        <Page />
      </main>
    </div>
  );
}
