from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, EmailStr, Field


class UserRole(Enum):
    """Represent an account's authorization role.

    Attributes
    ----------
    USER : UserRole
        Standard account with user-level permissions.
    ADMIN : UserRole
        Administrator account with ticket-management permissions.
    """

    USER = "user"
    ADMIN = "admin"


@dataclass
class User:
    """Represent a persisted account without credential material.

    Attributes
    ----------
    user_id : int
        Database identifier for the account.
    email : str
        Account email address.
    role : UserRole
        Authorization role assigned to the account.
    """

    user_id: int
    email: str
    role: UserRole


@dataclass
class AuthenticatedUser:
    """Represent an account authenticated by an active bearer token.

    Attributes
    ----------
    user : User
        Authenticated account.
    access_token : str
        Opaque bearer token issued to the account.
    expires_at : datetime
        Token expiration timestamp.
    """

    user: User
    access_token: str
    expires_at: datetime


@dataclass
class UserCredentials:
    """Represent an account with private authentication identifiers.

    Attributes
    ----------
    user : User
        Public account details.
    password_hash : str or None
        Stored password hash, or ``None`` for OAuth-only accounts.
    google_subject : str or None
        Linked Google subject, if any.
    """

    user: User
    password_hash: str | None
    google_subject: str | None


class RegistrationRequest(BaseModel):
    """Validate email and password account registration data.

    Attributes
    ----------
    email : EmailStr
        Email address for the new account.
    password : str
        Password meeting the configured length constraints.
    """

    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """Validate email and password login credentials.

    Attributes
    ----------
    email : EmailStr
        Email address of the account.
    password : str
        Account password.
    """

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Represent public account details returned by the API.

    Attributes
    ----------
    user_id : int
        Database identifier for the account.
    email : EmailStr
        Account email address.
    role : UserRole
        Authorization role assigned to the account.
    """

    user_id: int
    email: EmailStr
    role: UserRole


class AuthenticatedUserResponse(BaseModel):
    """Represent an issued bearer token and its account.

    Attributes
    ----------
    access_token : str
        Opaque bearer token.
    token_type : str
        Token scheme used for authorization.
    expires_at : datetime
        Token expiration timestamp.
    user : UserResponse
        Public account details.
    """

    access_token: str
    token_type: str
    expires_at: datetime
    user: UserResponse

    @classmethod
    def from_authenticated_user(cls, authenticated_user: AuthenticatedUser) -> Self:
        """Build a public response from an authenticated account.

        Parameters
        ----------
        authenticated_user : AuthenticatedUser
            Account and token returned by the authentication service.

        Returns
        -------
        Self
            API response containing the token and public account details.
        """
        user: User = authenticated_user.user
        return cls(
            access_token=authenticated_user.access_token,
            token_type="Bearer",
            expires_at=authenticated_user.expires_at,
            user=UserResponse(user_id=user.user_id, email=user.email, role=user.role),
        )
