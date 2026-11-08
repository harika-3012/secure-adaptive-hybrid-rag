"""Roles and document/space permission rules (single source of truth for access decisions)."""
from __future__ import annotations

from dataclasses import dataclass

ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_ADMIN, ROLE_EDITOR, ROLE_VIEWER)

VISIBILITY_PRIVATE = "private"  # owner and administrators only
VISIBILITY_SHARED = "shared"  # owner, administrators and the named users
VISIBILITY_ORGANIZATION = "organization"  # every active user
VISIBILITIES = (VISIBILITY_PRIVATE, VISIBILITY_SHARED, VISIBILITY_ORGANIZATION)


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def can_upload(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_EDITOR)


def can_read_document(p: Principal, doc: dict) -> bool:
    if p.is_admin or doc.get("owner_id") == p.user_id:
        return True
    visibility = doc.get("visibility")
    if visibility == VISIBILITY_ORGANIZATION:
        return True
    return visibility == VISIBILITY_SHARED and p.user_id in doc.get("shared_with", [])


def can_manage_document(p: Principal, doc: dict) -> bool:
    return p.is_admin or doc.get("owner_id") == p.user_id


def readable_document_filter(p: Principal) -> dict:
    """Mongo filter equivalent of can_read_document, applied in the database query."""
    if p.is_admin:
        return {}
    return {
        "$or": [
            {"owner_id": p.user_id},
            {"visibility": VISIBILITY_ORGANIZATION},
            {"visibility": VISIBILITY_SHARED, "shared_with": p.user_id},
        ]
    }


def can_read_space(p: Principal, space: dict) -> bool:
    return p.is_admin or space.get("owner_id") == p.user_id or p.user_id in space.get("member_ids", [])


def can_manage_space(p: Principal, space: dict) -> bool:
    return p.is_admin or space.get("owner_id") == p.user_id
