from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pymongo.errors import DuplicateKeyError

from app.api.deps import bearer_scheme, get_principal
from app.core.config import get_settings
from app.core.container import get_container
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.services.access_service import ROLE_ADMIN, ROLE_VIEWER, Principal
from app.services.user_service import public

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: dict) -> TokenOut:
    s = get_settings()
    token, _, expires_at = create_access_token(user["user_id"], s.jwt_secret, s.jwt_expire_minutes)
    return TokenOut(
        access_token=token,
        expires_at=expires_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
        user=UserOut(**user),
    )


@router.get("/setup-status")
def setup_status() -> dict:
    c = get_container()
    return {"needs_admin": c.users.count() == 0, "self_registration": get_settings().allow_self_registration}


@router.post("/register", response_model=TokenOut, status_code=201)
def register(req: RegisterRequest) -> TokenOut:
    s = get_settings()
    c = get_container()
    first_user = c.users.count() == 0
    if not first_user and not s.allow_self_registration:
        raise HTTPException(403, "Self-registration is disabled. Ask an administrator for an account.")
    email = req.email.strip().lower()
    if c.users.get_by_email(email):
        raise HTTPException(409, "An account with this email already exists.")
    role = ROLE_ADMIN if first_user else ROLE_VIEWER
    try:
        user = c.users.create(email, req.name.strip(), hash_password(req.password), role)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "An account with this email already exists.") from exc
    c.audit.record("auth.register", None, "user", user["user_id"], {"role": role}, actor_email=email)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(req: LoginRequest) -> TokenOut:
    c = get_container()
    email = req.email.strip().lower()
    record = c.users.get_by_email(email)
    if record is None or not verify_password(req.password, record["password_hash"]):
        c.audit.record("auth.login_failed", None, actor_email=email)
        raise HTTPException(401, "Invalid email or password.")
    if not record["active"]:
        c.audit.record("auth.login_blocked", None, "user", record["user_id"], actor_email=email)
        raise HTTPException(403, "This account has been disabled. Contact an administrator.")
    c.audit.record("auth.login", Principal(record["user_id"], email, record["name"], record["role"]))
    return _token_response(public(record))


@router.post("/logout", status_code=204)
def logout(p: Principal = Depends(get_principal), creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> None:
    c = get_container()
    payload = decode_access_token(creds.credentials, get_settings().jwt_secret)
    c.sessions.revoke(payload["jti"], datetime.fromtimestamp(payload["exp"], tz=timezone.utc))
    c.audit.record("auth.logout", p)


@router.get("/me", response_model=UserOut)
def me(p: Principal = Depends(get_principal)) -> UserOut:
    user = get_container().users.get_public(p.user_id)
    return UserOut(**user)
