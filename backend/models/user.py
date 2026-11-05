from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, EmailStr, Field


class UserRole(Enum):
    """Represent an account's authorization role."""

    USER = "user"
    ADMIN = "admin"


@dataclass
class User:
    """Represent a persisted user without exposing credential material."""

    user_id: int
    email: str
    role: UserRole


@dataclass
class AuthenticatedUser:
    """Represent an authenticated account and its active bearer token."""

    user: User
    access_token: str
    expires_at: datetime


@dataclass
class UserCredentials:
    """Represent a user together with private authentication identifiers."""

    user: User
    password_hash: str | None
    google_subject: str | None


class RegistrationRequest(BaseModel):
    """Represent email and password account registration details."""

    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """Represent email and password login credentials."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Represent public account details returned by the API."""

    user_id: int
    email: EmailStr
    role: UserRole


class AuthenticatedUserResponse(BaseModel):
    """Represent a bearer token and the account it authenticates."""

    access_token: str
    token_type: str
    expires_at: datetime
    user: UserResponse

    @classmethod
    def from_authenticated_user(cls, authenticated_user: AuthenticatedUser) -> Self:
        """Build a public response from an issued access token."""
        user: User = authenticated_user.user
        return cls(
            access_token=authenticated_user.access_token,
            token_type="Bearer",
            expires_at=authenticated_user.expires_at,
            user=UserResponse(user_id=user.user_id, email=user.email, role=user.role),
        )
