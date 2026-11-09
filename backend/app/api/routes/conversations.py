"""Conversation history: scoped question threads owned by the signed-in user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_principal
from app.core.container import get_container
from app.schemas.workspace import ConversationCreate, MessageCreate
from app.services.access_service import Principal
from app.services.assistant_service import ScopeError
from app.services.embedding_service import EmbeddingUnavailable
from app.services.generation_service import LLMUnavailable

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
NEW_TITLE = "New conversation"


def _load_owned(conversation_id: str, p: Principal) -> dict:
    conv = get_container().conversations.get_for_owner(p.user_id, conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found.")
    return conv


@router.get("")
def list_conversations(p: Principal = Depends(get_principal)) -> list[dict]:
    return get_container().conversations.list_for_owner(p.user_id)


@router.post("", status_code=201)
def create_conversation(req: ConversationCreate, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    scope = req.scope.model_dump()
    try:
        c.assistant.validate_scope(p, scope)
    except ScopeError as exc:
        raise HTTPException(404, str(exc)) from exc
    return c.conversations.create(p.user_id, scope, NEW_TITLE)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    conv = _load_owned(conversation_id, p)
    return {**conv, "messages": c.conversations.messages(conversation_id)}


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, p: Principal = Depends(get_principal)) -> None:
    if not get_container().conversations.delete(p.user_id, conversation_id):
        raise HTTPException(404, "Conversation not found.")


@router.post("/{conversation_id}/messages", status_code=201)
def ask(conversation_id: str, req: MessageCreate, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    conv = _load_owned(conversation_id, p)
    question = req.content.strip()
    user_msg = c.conversations.add_message(conv, "user", question)
    try:
        outcome = c.assistant.answer(p, conv["scope"], question, req.compare)
    except ScopeError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (EmbeddingUnavailable, LLMUnavailable) as exc:
        raise HTTPException(503, str(exc)) from exc
    assistant_msg = c.conversations.add_message(
        conv,
        "assistant",
        outcome.text,
        citations=[cit.model_dump() for cit in outcome.citations],
        sufficient_evidence=outcome.sufficient,
        compare=req.compare,
        note=outcome.note,
    )
    c.audit.record("qa.ask", p, "conversation", conversation_id, {"question_chars": len(question), "compare": req.compare})
    return {"user_message": user_msg, "assistant_message": assistant_msg}
