from app.core import container as container_module
from app.schemas.models import DocStatus, DocumentInfo
from tests.conftest import auth_header, register


def add_document(owner: dict, visibility: str, shared_with: list[str] | None = None) -> str:
    doc_id = f"doc-{visibility}-{owner['user_id'][:6]}-{len(shared_with or [])}"
    container_module.get_container().store.add(
        DocumentInfo(
            document_id=doc_id,
            filename="policy.txt",
            size_bytes=10,
            status=DocStatus.processed,
            uploaded_at="2026-01-01T00:00:00+00:00",
            owner_id=owner["user_id"],
            owner_name=owner["name"],
            visibility=visibility,
            shared_with=shared_with or [],
        )
    )
    return doc_id


def make_user(client, admin_token: str, email: str, role: str) -> dict:
    res = client.post(
        "/api/admin/users",
        json={"email": email, "name": "Staff Member", "password": "password123", "role": role},
        headers=auth_header(admin_token),
    )
    assert res.status_code == 201, res.text
    login = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200, login.text
    return {"user": login.json()["user"], "token": login.json()["access_token"]}


def test_first_account_becomes_administrator(client):
    assert client.get("/api/auth/setup-status").json()["needs_admin"] is True
    admin = register(client, "first@example.com", "First Admin")
    assert admin["user"]["role"] == "admin"
    assert client.get("/api/auth/setup-status").json()["needs_admin"] is False


def test_login_rejects_wrong_password(client):
    register(client, "user@example.com")
    res = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert res.status_code == 401


def test_logout_revokes_the_token(client):
    token = register(client, "logout@example.com")["access_token"]
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 200
    assert client.post("/api/auth/logout", headers=auth_header(token)).status_code == 204
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401


def test_private_document_is_hidden_from_viewer(client):
    admin = register(client, "admin@example.com")
    editor = make_user(client, admin["access_token"], "editor@example.com", "editor")
    viewer = make_user(client, admin["access_token"], "viewer@example.com", "viewer")
    doc_id = add_document(editor["user"], "private")

    assert client.get(f"/api/documents/{doc_id}", headers=auth_header(viewer["token"])).status_code == 404
    listed = client.get("/api/documents", headers=auth_header(viewer["token"])).json()
    assert doc_id not in [d["document_id"] for d in listed]
    assert client.get(f"/api/documents/{doc_id}", headers=auth_header(editor["token"])).status_code == 200


def test_shared_and_organization_documents_follow_their_rules(client):
    admin = register(client, "admin@example.com")
    editor = make_user(client, admin["access_token"], "editor@example.com", "editor")
    named = make_user(client, admin["access_token"], "named@example.com", "viewer")
    other = make_user(client, admin["access_token"], "other@example.com", "viewer")
    shared_id = add_document(editor["user"], "shared", [named["user"]["user_id"]])
    org_id = add_document(editor["user"], "organization")

    assert client.get(f"/api/documents/{shared_id}", headers=auth_header(named["token"])).status_code == 200
    assert client.get(f"/api/documents/{shared_id}", headers=auth_header(other["token"])).status_code == 404
    assert client.get(f"/api/documents/{org_id}", headers=auth_header(other["token"])).status_code == 200


def test_viewer_cannot_upload(client):
    admin = register(client, "admin@example.com")
    viewer = make_user(client, admin["access_token"], "viewer@example.com", "viewer")
    res = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"visibility": "private"},
        headers=auth_header(viewer["token"]),
    )
    assert res.status_code == 403


def test_viewer_cannot_use_administration(client):
    admin = register(client, "admin@example.com")
    viewer = make_user(client, admin["access_token"], "viewer@example.com", "viewer")
    assert client.get("/api/admin/users", headers=auth_header(viewer["token"])).status_code == 403


def test_space_scope_requires_read_access(client):
    admin = register(client, "admin@example.com")
    editor = make_user(client, admin["access_token"], "editor@example.com", "editor")
    viewer = make_user(client, admin["access_token"], "viewer@example.com", "viewer")
    space = client.post(
        "/api/spaces", json={"name": "Vendor Team", "description": ""}, headers=auth_header(editor["token"])
    )
    assert space.status_code == 201, space.text
    scope = {"scope": {"type": "space", "space_id": space.json()["space_id"]}}

    assert client.post("/api/conversations", json=scope, headers=auth_header(viewer["token"])).status_code == 404
    assert client.post("/api/conversations", json=scope, headers=auth_header(editor["token"])).status_code == 201


def test_documents_scope_rejects_unreadable_documents(client):
    admin = register(client, "admin@example.com")
    editor = make_user(client, admin["access_token"], "editor@example.com", "editor")
    viewer = make_user(client, admin["access_token"], "viewer@example.com", "viewer")
    private_id = add_document(editor["user"], "private")
    res = client.post(
        "/api/conversations",
        json={"scope": {"type": "documents", "document_ids": [private_id]}},
        headers=auth_header(viewer["token"]),
    )
    assert res.status_code == 404


def test_conversations_are_private_to_their_owner(client):
    admin = register(client, "admin@example.com")
    editor = make_user(client, admin["access_token"], "editor@example.com", "editor")
    viewer = make_user(client, admin["access_token"], "viewer@example.com", "viewer")
    conv = client.post("/api/conversations", json={"scope": {"type": "all"}}, headers=auth_header(editor["token"]))
    conv_id = conv.json()["conversation_id"]

    assert client.get(f"/api/conversations/{conv_id}", headers=auth_header(viewer["token"])).status_code == 404
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "What does the policy say?"},
        headers=auth_header(viewer["token"]),
    )
    assert res.status_code == 404


def test_sole_administrator_cannot_demote_themselves(client):
    admin = register(client, "admin@example.com")
    res = client.patch(
        f"/api/admin/users/{admin['user']['user_id']}",
        json={"role": "viewer"},
        headers=auth_header(admin["access_token"]),
    )
    assert res.status_code == 422
    assert client.get("/api/auth/me", headers=auth_header(admin["access_token"])).json()["role"] == "admin"


def test_administrator_can_disable_another_when_one_remains(client):
    admin = register(client, "admin@example.com")
    second = make_user(client, admin["access_token"], "second@example.com", "admin")
    res = client.patch(
        f"/api/admin/users/{second['user']['user_id']}",
        json={"active": False},
        headers=auth_header(admin["access_token"]),
    )
    assert res.status_code == 200
    assert client.get("/api/auth/me", headers=auth_header(second["token"])).status_code == 401
