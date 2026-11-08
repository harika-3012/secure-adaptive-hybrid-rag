"""MongoDB connection and index definitions."""
from __future__ import annotations

import uuid
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.core.config import get_settings


@lru_cache
def get_client() -> MongoClient:
    s = get_settings()
    return MongoClient(s.mongo_uri, serverSelectionTimeoutMS=s.mongo_timeout_ms, tz_aware=True)


def get_database() -> Database:
    return get_client()[get_settings().mongo_db]


def create_scratch_database() -> Database:
    """Throwaway database for evaluation runs, isolated from user data."""
    return get_client()[f"sahrag_scratch_{uuid.uuid4().hex[:12]}"]


def drop_database(db: Database) -> None:
    get_client().drop_database(db.name)


def ensure_indexes(db: Database) -> None:
    db.users.create_index("user_id", unique=True)
    db.users.create_index("email", unique=True)
    db.documents.create_index("document_id", unique=True)
    db.documents.create_index("owner_id")
    db.documents.create_index([("visibility", ASCENDING), ("team", ASCENDING)])
    db.chunks.create_index("chunk_id", unique=True)
    db.chunks.create_index("document_id")
    db.audit_logs.create_index([("at", DESCENDING)])
    db.revoked_tokens.create_index("jti", unique=True)
    db.revoked_tokens.create_index("expires_at", expireAfterSeconds=0)
