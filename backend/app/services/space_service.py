"""Knowledge Spaces: named collections of documents with their own members (MongoDB)."""
from __future__ import annotations

import uuid

from pymongo import ReturnDocument
from pymongo.database import Database

from app.utils.clock import now_iso


class SpaceRepository:
    def __init__(self, db: Database) -> None:
        self._col = db.spaces

    def create(self, owner_id: str, name: str, description: str) -> dict:
        doc = {
            "space_id": uuid.uuid4().hex[:12],
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "member_ids": [],
            "document_ids": [],
            "created_at": now_iso(),
        }
        self._col.insert_one(doc)
        return _clean(doc)

    def get(self, space_id: str) -> dict | None:
        doc = self._col.find_one({"space_id": space_id}, {"_id": 0})
        return doc

    def list_for_filter(self, query: dict) -> list[dict]:
        return list(self._col.find(query, {"_id": 0}).sort("created_at", -1))

    def update(self, space_id: str, **fields) -> dict | None:
        return self._col.find_one_and_update(
            {"space_id": space_id}, {"$set": fields}, projection={"_id": 0}, return_document=ReturnDocument.AFTER
        )

    def delete(self, space_id: str) -> None:
        self._col.delete_one({"space_id": space_id})

    def add_document(self, space_id: str, document_id: str) -> None:
        self._col.update_one({"space_id": space_id}, {"$addToSet": {"document_ids": document_id}})

    def remove_document(self, space_id: str, document_id: str) -> None:
        self._col.update_one({"space_id": space_id}, {"$pull": {"document_ids": document_id}})

    def remove_document_everywhere(self, document_id: str) -> None:
        self._col.update_many({}, {"$pull": {"document_ids": document_id}})

    def set_members(self, space_id: str, member_ids: list[str]) -> None:
        self._col.update_one({"space_id": space_id}, {"$set": {"member_ids": member_ids}})


def _clean(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}
