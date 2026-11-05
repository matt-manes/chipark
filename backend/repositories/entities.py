from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..models.ticket import TicketStatus
from ..models.user import UserRole


class Base(DeclarativeBase):
    """Base class for SQLAlchemy table mappings."""


class UserRecord(Base):
    """Map account credentials and roles to the ``users`` table.

    Attributes
    ----------
    user_id : Mapped[int]
        Primary key for the account.
    email : Mapped[str]
        Unique account email address.
    password_hash : Mapped[str or None]
        Password hash, if the account supports password login.
    google_subject : Mapped[str or None]
        Unique linked Google subject, if present.
    role : Mapped[UserRole]
        Account authorization role.
    """

    __tablename__: str = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    google_subject: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), nullable=False, default=UserRole.USER
    )


class AccessTokenRecord(Base):
    """Map bearer-token digests to their owners and lifecycle timestamps.

    Attributes
    ----------
    token_hash : Mapped[str]
        SHA-256 digest of the bearer token.
    user_id : Mapped[int]
        Identifier of the token owner.
    expires_at : Mapped[datetime]
        Token expiration timestamp.
    revoked_at : Mapped[datetime or None]
        Revocation timestamp, or ``None`` while active.
    """

    __tablename__: str = "access_tokens"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthStateRecord(Base):
    """Map one-time Google OAuth state to its PKCE verifier.

    Attributes
    ----------
    state_hash : Mapped[str]
        SHA-256 digest of the OAuth state value.
    code_verifier : Mapped[str]
        PKCE verifier associated with the state.
    expires_at : Mapped[datetime]
        State expiration timestamp.
    """

    __tablename__: str = "oauth_states"

    state_hash: Mapped[str] = mapped_column(String, primary_key=True)
    code_verifier: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ParkRecord(Base):
    """Map park model fields to the ``parks`` table."""

    __tablename__: str = "parks"

    park_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    park_no: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    street: Mapped[str | None] = mapped_column(String, nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String, nullable=True)
    acres: Mapped[str] = mapped_column(String, nullable=False)
    ward: Mapped[str] = mapped_column(String, nullable=False)
    park_class: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)


class TicketRecord(Base):
    """Map ticket model fields to the ``tickets`` table."""

    __tablename__: str = "tickets"

    ticket_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    park_name: Mapped[str] = mapped_column(ForeignKey("parks.name"), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False), nullable=False
    )
    file_date: Mapped[datetime] = mapped_column(nullable=False)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    issue: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
