"""Request and response schemas for sign-in and user accounts."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def _password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=200)


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    active: bool
    created_at: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserOut


class AdminCreateUser(RegisterRequest):
    role: Literal["admin", "editor", "viewer"] = "viewer"


class AdminUpdateUser(BaseModel):
    role: Literal["admin", "editor", "viewer"] | None = None
    active: bool | None = None
