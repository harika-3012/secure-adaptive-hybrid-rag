from app.services.access_service import (
    VISIBILITY_ORGANIZATION,
    VISIBILITY_PRIVATE,
    VISIBILITY_SHARED,
    Principal,
    can_manage_document,
    can_manage_space,
    can_read_document,
    can_read_space,
    readable_document_filter,
)

ADMIN = Principal("admin-1", "admin@example.com", "Admin", "admin")
EDITOR = Principal("editor-1", "editor@example.com", "Editor", "editor")
VIEWER = Principal("viewer-1", "viewer@example.com", "Viewer", "viewer")
OTHER = Principal("viewer-2", "other@example.com", "Other", "viewer")


def doc(visibility, shared_with=None, owner="editor-1"):
    return {"owner_id": owner, "visibility": visibility, "shared_with": shared_with or []}


def test_private_document_is_visible_to_owner_and_admin_only():
    d = doc(VISIBILITY_PRIVATE)
    assert can_read_document(EDITOR, d)
    assert can_read_document(ADMIN, d)
    assert not can_read_document(VIEWER, d)


def test_shared_document_is_visible_to_named_users_only():
    d = doc(VISIBILITY_SHARED, shared_with=["viewer-1"])
    assert can_read_document(VIEWER, d)
    assert not can_read_document(OTHER, d)


def test_organization_document_is_visible_to_everyone():
    assert can_read_document(OTHER, doc(VISIBILITY_ORGANIZATION))


def test_only_owner_or_admin_manage_documents():
    d = doc(VISIBILITY_ORGANIZATION)
    assert can_manage_document(EDITOR, d)
    assert can_manage_document(ADMIN, d)
    assert not can_manage_document(VIEWER, d)


def test_readable_filter_matches_python_rules():
    assert readable_document_filter(ADMIN) == {}
    clauses = readable_document_filter(VIEWER)["$or"]
    assert {"owner_id": "viewer-1"} in clauses
    assert {"visibility": VISIBILITY_ORGANIZATION} in clauses
    assert {"visibility": VISIBILITY_SHARED, "shared_with": "viewer-1"} in clauses


def test_space_membership_rules():
    space = {"owner_id": "editor-1", "member_ids": ["viewer-1"]}
    assert can_read_space(VIEWER, space)
    assert not can_read_space(OTHER, space)
    assert can_read_space(ADMIN, space)
    assert can_manage_space(EDITOR, space)
    assert not can_manage_space(VIEWER, space)
