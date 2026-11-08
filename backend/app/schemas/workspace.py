"""Request and response schemas for spaces, conversations, search and admin screens."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    label: str  # "S1"
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    excerpt: str
    cited_by_model: bool


class SpaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    description: str = Field("", max_length=500)


class SpaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=80)
    description: str | None = Field(None, max_length=500)


class SpaceDocumentAdd(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=64)


class SpaceMembersSet(BaseModel):
    member_ids: list[str] = Field(default_factory=list, max_length=500)


class ScopeIn(BaseModel):
    type: Literal["all", "space", "documents"] = "all"
    space_id: Optional[str] = None
    document_ids: list[str] = Field(default_factory=list, max_length=50)


class ConversationCreate(BaseModel):
    scope: ScopeIn = Field(default_factory=ScopeIn)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=2, max_length=2000)
    compare: bool = False


class DocumentAccessUpdate(BaseModel):
    visibility: Literal["private", "shared", "organization"]
    shared_with: list[str] = Field(default_factory=list, max_length=500)
