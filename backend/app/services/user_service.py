"""User accounts (MongoDB)."""
from __future__ import annotations

import uuid

from pymongo import ReturnDocument
from pymongo.database import Database

from app.utils.clock import now_iso

_HIDDEN = {"_id": 0, "password_hash": 0}


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._col = db.users

    def count(self) -> int:
        return self._col.count_documents({})

    def create(self, email: str, name: str, password_hash: str, role: str) -> dict:
        doc = {
            "user_id": uuid.uuid4().hex,
            "email": email,
            "name": name,
            "password_hash": password_hash,
            "role": role,
            "active": True,
            "created_at": now_iso(),
        }
        self._col.insert_one(doc)
        return public(doc)

    def get_by_email(self, email: str) -> dict | None:
        return self._col.find_one({"email": email}, {"_id": 0})

    def get_by_id(self, user_id: str) -> dict | None:
        return self._col.find_one({"user_id": user_id}, {"_id": 0})

    def get_public(self, user_id: str) -> dict | None:
        return self._col.find_one({"user_id": user_id}, _HIDDEN)

    def list_public(self) -> list[dict]:
        return list(self._col.find({}, _HIDDEN).sort("created_at", 1))

    def list_active_directory(self) -> list[dict]:
        return list(self._col.find({"active": True}, {"_id": 0, "user_id": 1, "name": 1, "email": 1}).sort("name", 1))

    def update(self, user_id: str, **fields) -> dict | None:
        doc = self._col.find_one_and_update(
            {"user_id": user_id}, {"$set": fields}, projection=_HIDDEN, return_document=ReturnDocument.AFTER
        )
        return doc

    def active_ids(self, user_ids: list[str]) -> set[str]:
        if not user_ids:
            return set()
        found = self._col.find({"user_id": {"$in": user_ids}, "active": True}, {"user_id": 1})
        return {d["user_id"] for d in found}


def public(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "password_hash"}
