"""Append-only audit trail of security-relevant actions (MongoDB)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pymongo.database import Database

from app.services.access_service import Principal


class AuditLog:
    def __init__(self, db: Database) -> None:
        self._col = db.audit_logs

    def record(
        self,
        action: str,
        actor: Principal | None,
        target_type: str = "",
        target_id: str = "",
        details: dict | None = None,
        actor_email: str = "",
    ) -> None:
        self._col.insert_one(
            {
                "event_id": uuid.uuid4().hex,
                "at": datetime.now(timezone.utc),
                "action": action,
                "actor_id": actor.user_id if actor else "",
                "actor_email": actor.email if actor else actor_email,
                "target_type": target_type,
                "target_id": target_id,
                "details": details or {},
            }
        )

    def list(self, action: str | None = None, actor_id: str | None = None, limit: int = 200) -> list[dict]:
        query: dict = {}
        if action:
            query["action"] = action
        if actor_id:
            query["actor_id"] = actor_id
        rows = self._col.find(query, {"_id": 0}).sort("at", -1).limit(limit)
        return [_jsonable(r) for r in rows]


def _jsonable(row: dict) -> dict:
    row["at"] = row["at"].isoformat(timespec="seconds")
    return row
