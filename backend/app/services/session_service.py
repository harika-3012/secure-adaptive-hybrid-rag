"""Revoked access tokens (logout)."""
from __future__ import annotations

from datetime import datetime

from pymongo.database import Database


class SessionRevocations:
    def __init__(self, db: Database) -> None:
        self._col = db.revoked_tokens

    def revoke(self, jti: str, expires_at: datetime) -> None:
        self._col.update_one(
            {"jti": jti}, {"$setOnInsert": {"jti": jti, "expires_at": expires_at}}, upsert=True
        )

    def is_revoked(self, jti: str) -> bool:
        return self._col.find_one({"jti": jti}, {"_id": 1}) is not None
