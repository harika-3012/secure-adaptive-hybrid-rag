from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, conversations, documents, evaluation, spaces, workspace
from app.core.config import get_settings

app = FastAPI(
    title="Secure Adaptive Hybrid RAG",
    description="Enterprise document intelligence: permission-aware Q&A with citations, running on local models.",
    version="0.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth.router, documents.router, spaces.router, conversations.router, workspace.router, admin.router, evaluation.router):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
