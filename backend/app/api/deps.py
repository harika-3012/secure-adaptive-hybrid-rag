"""Request dependencies: the signed-in principal and role checks."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.container import get_container
from app.core.security import decode_access_token
from app.services.access_service import Principal

bearer_scheme = HTTPBearer(auto_error=False)


def get_principal(creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> Principal:
    unauthorized = HTTPException(401, "Please sign in again.", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    c = get_container()
    try:
        payload = decode_access_token(creds.credentials, get_settings().jwt_secret)
    except jwt.PyJWTError as exc:
        raise unauthorized from exc
    if c.sessions.is_revoked(payload["jti"]):
        raise unauthorized
    user = c.users.get_by_id(payload["sub"])
    if user is None or not user["active"]:
        raise unauthorized
    return Principal(user["user_id"], user["email"], user["name"], user["role"])


def require_editor(p: Principal = Depends(get_principal)) -> Principal:
    if not p.can_upload:
        raise HTTPException(403, "Your role cannot add or change documents.")
    return p


def require_admin(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_admin:
        raise HTTPException(403, "Administrator access is required.")
    return p
