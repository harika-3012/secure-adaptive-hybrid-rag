"""Shared test setup: an isolated data directory, a fixed token secret, and an in-memory MongoDB per test."""
from __future__ import annotations

import os
import tempfile
import uuid

_DATA = tempfile.mkdtemp(prefix="sahrag_test_")
os.environ["DATA_DIR"] = _DATA
os.environ["CHROMA_DIR"] = os.path.join(_DATA, "chroma")
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-production-0123456789"
os.environ["ALLOW_SELF_REGISTRATION"] = "true"

import mongomock  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import container as container_module  # noqa: E402
from app.core.container import Container  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    db = mongomock.MongoClient()[f"test_{uuid.uuid4().hex}"]
    monkeypatch.setattr(container_module, "_container", Container(db=db))
    return TestClient(app)


def register(client: TestClient, email: str, name: str = "Test User", password: str = "password123") -> dict:
    res = client.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
