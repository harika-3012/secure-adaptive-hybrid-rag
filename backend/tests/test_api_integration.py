"""Integration tests for upload -> processing -> retrieval -> chat -> persistence -> delete.

STATUS: written but NOT YET EXECUTED (the authoring sandbox could not install fastapi/chromadb/etc.).
Run locally with:  pytest backend/tests -q

To keep tests fast and offline, a deterministic hashing embedder replaces the SentenceTransformer model and
the Ollama call is stubbed -- in these tests only. The application itself never mocks either.
"""
import re
import zlib

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("chromadb")
pytest.importorskip("rank_bm25")
pytest.importorskip("pydantic_settings")

from fastapi.testclient import TestClient  # noqa: E402

DOC = (
    "POL-SEC-007 Password Management\nPasswords must contain at least 12 characters and must be changed every 90 days. "
    "Multi-factor authentication is mandatory for all privileged accounts.\n\n"
    "POL-SEC-023 Remote Work\nEmployees working remotely must connect through the approved corporate VPN. "
    "Screens must lock automatically after 5 minutes of inactivity.\n"
)


def _hash_embed(texts):
    out = np.zeros((len(texts), 256))
    for i, t in enumerate(texts):
        for w in re.findall(r"[a-z0-9]+", t.lower()):
            out[i, zlib.crc32(w.encode()) % 256] += 1.0
        n = np.linalg.norm(out[i])
        if n:
            out[i] /= n
    return out


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    from app.core import config, container

    config.get_settings.cache_clear()
    container.reset_container()

    from app.services.embedding_service import EmbeddingService
    from app.services.generation_service import GenerationService

    monkeypatch.setattr(EmbeddingService, "embed", lambda self, texts: _hash_embed(texts))
    monkeypatch.setattr(GenerationService, "_call_ollama", lambda self, q, ctx: "Passwords need 12 characters [S1] [S9].")

    from app.main import app

    yield TestClient(app)
    container.reset_container()
    config.get_settings.cache_clear()


def _upload(client, name="policy.txt", content=DOC.encode()):
    return client.post("/api/documents/upload", files={"file": (name, content, "text/plain")})


def test_upload_processes_and_lists(client):
    r = _upload(client)
    assert r.status_code == 202
    doc_id = r.json()["document_id"]
    status = client.get(f"/api/documents/{doc_id}/status").json()
    assert status["status"] == "processed" and status["chunks"] >= 1
    assert [d["document_id"] for d in client.get("/api/documents").json()] == [doc_id]


def test_upload_validation(client):
    assert _upload(client, "evil.exe", b"x").status_code == 415
    assert _upload(client, "empty.txt", b"").status_code == 400


def test_all_four_methods_return_cited_pages(client):
    _upload(client)
    for method in ("bm25", "dense", "fixed_hybrid", "adaptive_hybrid"):
        r = client.post("/api/retrieval/search", json={"query": "POL-SEC-007 password", "method": method, "top_k": 3})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["results"] and body["results"][0]["chunk"]["page"] == 1
        assert (body["adaptive"] is not None) == (method == "adaptive_hybrid")
    adaptive = body["adaptive"]
    assert adaptive["query_class"] == "identifier"
    assert abs(adaptive["bm25_weight"] + adaptive["dense_weight"] - 1) < 1e-6


def test_chat_citations_only_reference_retrieved_chunks(client):
    _upload(client)
    r = client.post("/api/chat/query", json={"query": "What does POL-SEC-007 require?", "method": "adaptive_hybrid"})
    assert r.status_code == 200, r.text
    body = r.json()
    labels = {c["label"] for c in body["citations"]}
    cited = {c["label"] for c in body["citations"] if c["cited_by_model"]}
    assert "S1" in cited and "S9" not in labels  # invented label [S9] is dropped


def test_unrelated_question_gets_insufficient_evidence_without_calling_llm(client, monkeypatch):
    from app.services.generation_service import INSUFFICIENT, GenerationService

    _upload(client)
    monkeypatch.setattr(GenerationService, "_call_ollama", lambda *a: pytest.fail("LLM must not be called"))
    r = client.post("/api/chat/query", json={"query": "cafeteria menu friday dessert", "method": "dense"})
    assert r.status_code == 200
    assert r.json()["answer"] == INSUFFICIENT


def test_persistence_after_restart_and_delete(client):
    from app.core import container

    doc_id = _upload(client).json()["document_id"]
    container.reset_container()  # simulate restart: services rebuilt from disk
    assert client.get(f"/api/documents/{doc_id}").json()["status"] == "processed"
    r = client.post("/api/retrieval/search", json={"query": "VPN", "method": "bm25"})
    assert r.status_code == 200 and r.json()["results"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.get(f"/api/documents/{doc_id}").status_code == 404
    assert client.post("/api/retrieval/search", json={"query": "VPN", "method": "bm25"}).status_code == 409
