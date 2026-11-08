"""Password hashing and signed access tokens."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72  # bcrypt limit


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, secret: str, expire_minutes: int) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    jti = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    token = jwt.encode({"sub": user_id, "jti": jti, "exp": expires_at}, secret, algorithm=ALGORITHM)
    return token, jti, expires_at


def decode_access_token(token: str, secret: str) -> dict:
    """Raises jwt.PyJWTError when the token is invalid, tampered with or expired."""
    return jwt.decode(token, secret, algorithms=[ALGORITHM], options={"require": ["sub", "jti", "exp"]})
