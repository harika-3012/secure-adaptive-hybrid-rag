# Implementation progress (Review 2)

Legend: **Verified** = executed with passing result in the authoring environment. **Written** = source complete but never executed (the authoring sandbox blocked PyPI/npm/HuggingFace, so heavy dependencies could not be installed). Treat "Written" items as untested until you run them.

| # | Component | Status |
|---|---|---|
| 1 | Project structure, config, `.env.example`, Windows scripts | Written (scripts not run; config module needs `pydantic-settings`) |
| 2 | Upload / list / get / status / delete API, file-type + size validation | Written |
| 3 | PDF / DOCX / TXT extraction with page numbers | Written |
| 4 | Cleaning + recursive chunking | **Verified** (4 unit tests) |
| 5 | Local embeddings + ChromaDB persistence | Written |
| 6 | BM25 retrieval | Written |
| 7 | Dense retrieval | Written |
| 8 | Score normalisation + fusion (fixed hybrid maths) | **Verified** (unit tests) |
| 9 | Adaptive query analysis, classification, α(q) | **Verified** (unit tests on rules/weights); retrieval benefit **not measured** |
| 10 | Ollama generation, evidence gate, citation filtering | Written |
| 11 | React frontend (4 pages) | Written (not built or opened) |
| 12 | Metrics (P@K, R@K, MRR, NDCG@K) | **Verified** (unit tests) |
| 13 | Evaluation aggregation + charts | **Verified** (unit test; chart rendering checked on a throwaway fixture) |
| 14 | Evaluation run over the corpus (`experiments/evaluation.py`) | Written; **no results exist yet** |
| 15 | Synthetic corpus + 24-question dataset | **Verified** (every evidence phrase checked against its document) |
| 16 | API integration tests | Written, not executed |

## Test results so far
`pytest backend/tests` in the authoring sandbox: 21 passed (chunking, adaptive/fusion, metrics, aggregation, corpus integrity). `test_api_integration.py` skips itself when fastapi/chromadb/rank-bm25/pydantic-settings are missing; it has not run.

## Preliminary results
None have been generated. After `python experiments/evaluation.py` runs locally, paste `experiments/results/summary_overall.csv` here and keep the PRELIMINARY label. Do not claim adaptive retrieval is better unless the numbers show it.

## Screenshots checklist (take after a local run)
- [ ] Dashboard with model status
- [ ] Upload page: file in `processing` then `processed`
- [ ] Ask page: answer with expanded source
- [ ] Insufficient-evidence reply for an unrelated question
- [ ] Retrieval comparison: all four columns for one query
- [ ] Adaptive panel for an identifier query and a conceptual query (different weights)
- [ ] Evaluation table + charts
- [ ] Swagger UI at http://127.0.0.1:8000/docs
- [ ] Terminal showing `pytest` result

## Demonstration script
1. `scripts\run_backend.bat`, `scripts\run_frontend.bat`; open http://localhost:5173.
2. Dashboard: confirm Ollama "Ready".
3. Documents: upload `data/evaluation/corpus/syn-infosec.txt` (synthetic) and a public PDF (e.g. an RBI circular you download yourself); show status → processed.
4. Retrieval comparison: query `POL-SEC-007` – BM25 / dense / fixed / adaptive columns; note the adaptive class *identifier* and weights.
5. Same page: query `Why should we protect data when staff work from home?` – note the class and weight shift toward dense.
6. Ask: `What does POL-SEC-007 require?` – answer, expand sources.
7. Ask something absent (`cafeteria menu`) – insufficient-evidence reply.
8. Run evaluation; discuss the PRELIMINARY table and the limitations.

## Implemented vs planned
Implemented (code written): everything above. Planned, not started: authentication, RBAC, permission-aware retrieval, document classification, cross-encoder reranking, learned α, evidence-sufficiency verifier model, audit logs, multi-user, OCR for scanned PDFs, air-gapped packaging, larger public-document evaluation.

## Future work
Learn α(q) from labelled queries; reranking; permission-aware retrieval and audit logging; NLI-based answer verification; larger independent evaluation on public regulatory documents; deployment hardening for fully air-gapped use.
