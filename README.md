# Knowledge Assistant (Secure Adaptive Hybrid RAG)

A local-first document assistant for teams. Users sign in, upload documents, control who can see each one, group them into Knowledge Spaces, and ask questions in plain language. Every answer is grounded in the documents the user is allowed to read and cites its sources.

## Stack

- Frontend: React + Vite
- Backend: Python FastAPI
- Users, document metadata, chunks, spaces, conversations, audit log: MongoDB
- Vector search: ChromaDB, with local sentence-transformers embeddings
- Answers: Ollama running a local model (default `qwen2.5:3b`)
- Original files: local filesystem under `data/documents`

No cloud services are used.

## Running locally (Windows, VS Code)

1. Install and start MongoDB Community Server (default `mongodb://127.0.0.1:27017`).
2. Install Ollama and pull the model: `ollama pull qwen2.5:3b`.
3. Run `scripts\setup.bat`. It creates the Python environment, installs frontend packages, creates `backend\.env`, and generates `JWT_SECRET`.
4. Optional: run `python scripts\verify_models.py` to check the embedding model and Ollama.
5. Start the backend with `scripts\run_backend.bat` and the frontend with `scripts\run_frontend.bat`.
6. Open the frontend address printed in the terminal (default `http://localhost:5173`).

The first account you create becomes the administrator. Afterwards, set `ALLOW_SELF_REGISTRATION=false` in `backend\.env` if only administrators should create accounts.

## Roles and access

| Role | Can do |
| --- | --- |
| Administrator | Everything, including user management, the audit trail, and system status |
| Editor | Upload documents, create spaces, manage their own documents and spaces |
| Viewer | Read documents shared with them, ask questions, search |

Each document has a visibility setting:

- Only me and administrators (private)
- Selected people (shared)
- Everyone in the organization

Access is enforced on the server in three places: route checks, database filters for listings, and document filters applied before retrieval. A question never reads text the user cannot open.

## Audit trail

Sign-ins, failed sign-ins, registrations, uploads, access changes, deletions, space and user administration, and questions are recorded. Questions are logged by length only, not by text.

## Tests

Backend tests live in `backend\tests`. Run them from the backend folder with the virtual environment active:

```
pytest
```

`test_access.py` and `test_intelligence.py` need no database or model.

## Project layout

- `backend/app/api/routes`: HTTP endpoints by area (auth, documents, spaces, conversations, admin, search)
- `backend/app/services`: access rules, retrieval, generation, document intelligence, storage
- `backend/app/core`: settings, database setup, service wiring, security
- `frontend/src/pages`: Ask, Search, Documents, Spaces, Administration, sign-in
- `docs/`: architecture and implementation notes
