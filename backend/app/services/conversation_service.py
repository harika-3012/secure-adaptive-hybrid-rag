"""Conversations and messages (MongoDB). Conversations are private to their owner."""
from __future__ import annotations

import uuid

from pymongo.database import Database

from app.utils.clock import now_iso

TITLE_CHARS = 60


class ConversationRepository:
    def __init__(self, db: Database) -> None:
        self._conversations = db.conversations
        self._messages = db.messages

    def create(self, owner_id: str, scope: dict, title: str) -> dict:
        doc = {
            "conversation_id": uuid.uuid4().hex,
            "owner_id": owner_id,
            "title": title,
            "scope": scope,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self._conversations.insert_one(doc)
        return _clean(doc)

    def list_for_owner(self, owner_id: str) -> list[dict]:
        return list(
            self._conversations.find({"owner_id": owner_id}, {"_id": 0}).sort("updated_at", -1)
        )

    def get_for_owner(self, owner_id: str, conversation_id: str) -> dict | None:
        return self._conversations.find_one(
            {"owner_id": owner_id, "conversation_id": conversation_id}, {"_id": 0}
        )

    def delete(self, owner_id: str, conversation_id: str) -> bool:
        res = self._conversations.delete_one({"owner_id": owner_id, "conversation_id": conversation_id})
        if res.deleted_count:
            self._messages.delete_many({"conversation_id": conversation_id})
        return res.deleted_count == 1

    def messages(self, conversation_id: str) -> list[dict]:
        return list(
            self._messages.find({"conversation_id": conversation_id}, {"_id": 0}).sort("created_at", 1)
        )

    def add_message(self, conversation: dict, role: str, content: str, **extra) -> dict:
        doc = {
            "message_id": uuid.uuid4().hex,
            "conversation_id": conversation["conversation_id"],
            "role": role,
            "content": content,
            "created_at": now_iso(),
            **extra,
        }
        self._messages.insert_one(doc)
        update = {"updated_at": doc["created_at"]}
        if not conversation.get("title") or conversation.get("title") == "New conversation":
            update["title"] = content[:TITLE_CHARS]
        self._conversations.update_one({"conversation_id": conversation["conversation_id"]}, {"$set": update})
        return _clean(doc)


def _clean(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}
