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


class ConditionsRecord(Base):
    """Map cached weather conditions to the ``conditions`` table.

    Attributes
    ----------
    park_id : Mapped[int]
        Primary key and foreign key identifying the park.
    last_updated : Mapped[datetime]
        Weather provider's observation update time.
    temp_f : Mapped[float]
        Temperature in degrees Fahrenheit.
    condition : Mapped[str]
        Text description of current weather.
    wind_mph : Mapped[float]
        Wind speed in miles per hour.
    wind_dir : Mapped[str]
        Cardinal direction of the wind.
    precip_in : Mapped[float]
        Precipitation in inches.
    humidity : Mapped[float]
        Relative humidity percentage.
    cloud : Mapped[float]
        Cloud cover percentage.
    feels_like_f : Mapped[float]
        Feels-like temperature in degrees Fahrenheit.
    heat_index_f : Mapped[float]
        Heat index in degrees Fahrenheit.
    uv : Mapped[float]
        Ultraviolet index.
    chance_of_rain : Mapped[float]
        Chance of rain as a percentage.
    chance_of_snow : Mapped[float]
        Chance of snow as a percentage.
    """

    __tablename__: str = "conditions"

    park_id: Mapped[int] = mapped_column(
        ForeignKey("parks.park_id", ondelete="CASCADE"), primary_key=True
    )
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temp_f: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String, nullable=False)
    wind_mph: Mapped[float] = mapped_column(Float, nullable=False)
    wind_dir: Mapped[str] = mapped_column(String, nullable=False)
    precip_in: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    cloud: Mapped[float] = mapped_column(Float, nullable=False)
    feels_like_f: Mapped[float] = mapped_column(Float, nullable=False)
    heat_index_f: Mapped[float] = mapped_column(Float, nullable=False)
    uv: Mapped[float] = mapped_column(Float, nullable=False)
    chance_of_rain: Mapped[float] = mapped_column(Float, nullable=False)
    chance_of_snow: Mapped[float] = mapped_column(Float, nullable=False)


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


class NotificationRecord(Base):
    """Map user ticket notifications to the ``notifications`` table."""

    __tablename__: str = "notifications"

    notification_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    ticket_id: Mapped[int] = mapped_column(Integer, nullable=False)
    park_name: Mapped[str] = mapped_column(String, nullable=False)
    issue: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
