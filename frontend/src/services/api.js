export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API}${path}`, options);
  } catch {
    throw new Error(`Cannot reach the backend at ${API}. Is it running (scripts\\run_backend.bat)?`);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  status: () => request("/api/status"),
  listDocuments: () => request("/api/documents"),
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/documents/upload", { method: "POST", body: form });
  },
  deleteDocument: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),
  search: (body) => request("/api/retrieval/search", json(body)),
  chat: (body) => request("/api/chat/query", json(body)),
  retrievalConfig: () => request("/api/retrieval/config"),
  runEvaluation: (body) => request("/api/evaluation/run", json(body)),
  evaluationResults: () => request("/api/evaluation/results"),
  chartUrl: (name) => `${API}/api/evaluation/charts/${name}`,
};

export const METHODS = [
  { value: "bm25", label: "BM25" },
  { value: "dense", label: "Dense" },
  { value: "fixed_hybrid", label: "Fixed hybrid" },
  { value: "adaptive_hybrid", label: "Adaptive hybrid" },
];
