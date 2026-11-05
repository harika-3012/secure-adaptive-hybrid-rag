from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, evaluation, retrieval
from app.core.config import get_settings

app = FastAPI(
    title="Secure Adaptive Hybrid RAG",
    description="Review 2 prototype: BM25 / dense / fixed hybrid / adaptive hybrid retrieval with local-LLM answers.",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (documents.router, chat.router, retrieval.router, evaluation.router):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
