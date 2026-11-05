# Secure Adaptive Hybrid RAG – Review 2 prototype

Query-adaptive hybrid retrieval (BM25 + dense) with a local LLM (Ollama) for privacy-preserving enterprise document Q&A. Everything runs locally; no cloud API is used.

> **Honest status:** all source code is written, but only the pure-Python parts (chunking, adaptive rules, fusion, metrics, aggregation, corpus checks – 21 tests) were executed in the authoring environment. The backend services, API, frontend and evaluation run need your first local execution. See `docs/implementation.md`. No evaluation numbers exist yet.

## Windows setup
Prerequisites: Python 3.10+, Node.js 18+, [Ollama](https://ollama.com).

```bat
scripts\setup.bat
ollama pull qwen2.5:3b
backend\.venv\Scripts\activate
python scripts\verify_models.py
```
`qwen2.5:3b` suits ~8 GB RAM machines; set `OLLAMA_MODEL` in `backend\.env` for another model (e.g. `llama3.2:3b`, `mistral`).

Run (two terminals):
```bat
scripts\run_backend.bat     REM http://127.0.0.1:8000/docs (Swagger)
scripts\run_frontend.bat    REM http://localhost:5173
```

### Air-gapped embedding model
The first run downloads `all-MiniLM-L6-v2` from Hugging Face. For offline machines, download it once elsewhere, copy the folder, and set `EMBEDDING_MODEL_PATH` in `backend\.env`.

## Tests and evaluation
```bat
cd backend && pytest tests -q
cd .. && python experiments\evaluation.py --k 5
```
Results go to `experiments\results\` (`results.json`, CSVs, PNG charts). The same evaluation is available from the Retrieval comparison page and `POST /api/evaluation/run`.

## Data
`data/evaluation/corpus/` holds four **synthetic** documents used for evaluation. For the demo, also download genuinely public documents (e.g. RBI circulars) yourself and upload them; never use confidential documents.

## Layout and docs
`backend/app` (API + services), `frontend/src`, `experiments/` (metrics, charts, CLI), `data/`, `scripts/`, `docs/` (architecture, methodology, implementation progress, demo script).

## API
`POST /api/documents/upload`, `GET /api/documents`, `GET|DELETE /api/documents/{id}`, `GET /api/documents/{id}/status`, `POST /api/chat/query`, `POST /api/retrieval/search`, `GET /api/retrieval/config`, `POST /api/evaluation/run`, `GET /api/evaluation/results`, plus `GET /api/status`.
