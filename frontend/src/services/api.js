const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const TOKEN_KEY = "sahrag.token";

export const session = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, form, raw } = {}) {
  const headers = {};
  const token = session.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check that the backend is running.");
  }
  if (res.status === 401 && token && !path.startsWith("/api/auth/")) {
    session.clear();
    window.dispatchEvent(new Event("session-expired"));
  }
  if (res.status === 204) return null;
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join(" ");
    } catch {
      /* non-JSON error body keeps the generic message */
    }
    throw new ApiError(res.status, message);
  }
  return raw ? res : res.json();
}

export const api = {
  setupStatus: () => request("/api/auth/setup-status"),
  register: (data) => request("/api/auth/register", { method: "POST", body: data }),
  login: (data) => request("/api/auth/login", { method: "POST", body: data }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),

  status: () => request("/api/status"),
  search: (q, limit = 8) => request(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  directory: () => request("/api/users/directory"),

  documents: () => request("/api/documents"),
  document: (id) => request(`/api/documents/${id}`),
  documentStatus: (id) => request(`/api/documents/${id}/status`),
  upload: (file, visibility, sharedWith) => {
    const form = new FormData();
    form.append("file", file);
    form.append("visibility", visibility);
    form.append("shared_with", sharedWith.join(","));
    return request("/api/documents/upload", { method: "POST", form });
  },
  updateAccess: (id, data) => request(`/api/documents/${id}/access`, { method: "PUT", body: data }),
  summarize: (id, refresh = false) =>
    request(`/api/documents/${id}/summary?refresh=${refresh}`, { method: "POST" }),
  deleteDocument: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),

  spaces: () => request("/api/spaces"),
  space: (id) => request(`/api/spaces/${id}`),
  createSpace: (data) => request("/api/spaces", { method: "POST", body: data }),
  updateSpace: (id, data) => request(`/api/spaces/${id}`, { method: "PATCH", body: data }),
  deleteSpace: (id) => request(`/api/spaces/${id}`, { method: "DELETE" }),
  addSpaceDocument: (id, documentId) =>
    request(`/api/spaces/${id}/documents`, { method: "POST", body: { document_id: documentId } }),
  removeSpaceDocument: (id, documentId) =>
    request(`/api/spaces/${id}/documents/${documentId}`, { method: "DELETE" }),
  setSpaceMembers: (id, memberIds) =>
    request(`/api/spaces/${id}/members`, { method: "PUT", body: { member_ids: memberIds } }),

  conversations: () => request("/api/conversations"),
  conversation: (id) => request(`/api/conversations/${id}`),
  createConversation: (scope) => request("/api/conversations", { method: "POST", body: { scope } }),
  deleteConversation: (id) => request(`/api/conversations/${id}`, { method: "DELETE" }),
  ask: (id, content, compare = false) =>
    request(`/api/conversations/${id}/messages`, { method: "POST", body: { content, compare } }),

  users: () => request("/api/admin/users"),
  createUser: (data) => request("/api/admin/users", { method: "POST", body: data }),
  updateUser: (id, data) => request(`/api/admin/users/${id}`, { method: "PATCH", body: data }),
  audit: (params = "") => request(`/api/admin/audit${params}`),
  system: () => request("/api/admin/system"),
};
