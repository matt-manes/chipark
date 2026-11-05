from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.user import User, UserCredentials, UserRole
from .entities import AccessTokenRecord, OAuthStateRecord, UserRecord


class AuthRepository:
    """Persist users, bearer tokens, and one-time OAuth state."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Create an authentication repository."""
        self._session_factory: sessionmaker[Session] = session_factory

    def create_user(
        self,
        email: str,
        password_hash: str | None,
        google_subject: str | None = None,
    ) -> User:
        """Create a regular user account."""
        with self._session_factory.begin() as session:
            record: UserRecord = UserRecord(
                email=email,
                password_hash=password_hash,
                google_subject=google_subject,
                role=UserRole.USER,
            )
            session.add(record)
            session.flush()
            return self._to_user(record)

    def get_credentials_by_email(self, email: str) -> UserCredentials | None:
        """Retrieve an account and private credential fields by email."""
        with self._session_factory() as session:
            record: UserRecord | None = session.scalar(
                select(UserRecord).where(UserRecord.email == email)
            )
            if record is None:
                return None
            return UserCredentials(
                user=self._to_user(record),
                password_hash=record.password_hash,
                google_subject=record.google_subject,
            )

    def get_user_by_google_subject(self, google_subject: str) -> User | None:
        """Retrieve an account associated with a Google subject identifier."""
        with self._session_factory() as session:
            record: UserRecord | None = session.scalar(
                select(UserRecord).where(UserRecord.google_subject == google_subject)
            )
            return None if record is None else self._to_user(record)

    def link_google_account(self, email: str, google_subject: str) -> User:
        """Link a verified Google identity to an email-matched account."""
        with self._session_factory.begin() as session:
            record: UserRecord | None = session.scalar(
                select(UserRecord).where(UserRecord.email == email)
            )
            if record is None:
                record = UserRecord(
                    email=email,
                    password_hash=None,
                    google_subject=google_subject,
                    role=UserRole.USER,
                )
                session.add(record)
            elif record.google_subject not in (None, google_subject):
                raise ValueError(
                    "This email is already linked to another Google account."
                )
            else:
                record.google_subject = google_subject
            session.flush()
            return self._to_user(record)

    def ensure_admin(self, email: str, password_hash: str) -> User:
        """Create the configured administrator or promote its existing account."""
        with self._session_factory.begin() as session:
            record: UserRecord | None = session.scalar(
                select(UserRecord).where(UserRecord.email == email)
            )
            if record is None:
                record = UserRecord(
                    email=email,
                    password_hash=password_hash,
                    role=UserRole.ADMIN,
                )
                session.add(record)
            else:
                record.role = UserRole.ADMIN
                record.password_hash = password_hash
            session.flush()
            return self._to_user(record)

    def has_admin(self) -> bool:
        """Return whether the database contains an administrator account."""
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(UserRecord.user_id)
                    .where(UserRecord.role == UserRole.ADMIN)
                    .limit(1)
                )
                is not None
            )

    def add_access_token(
        self, token_hash: str, user_id: int, expires_at: datetime
    ) -> None:
        """Persist a hashed bearer token."""
        with self._session_factory.begin() as session:
            session.add(
                AccessTokenRecord(
                    token_hash=token_hash,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )

    def get_user_for_token(self, token_hash: str, now: datetime) -> User | None:
        """Return the token owner if its token is active and unexpired."""
        with self._session_factory() as session:
            record: UserRecord | None = session.scalar(
                select(UserRecord)
                .join(
                    AccessTokenRecord, AccessTokenRecord.user_id == UserRecord.user_id
                )
                .where(
                    AccessTokenRecord.token_hash == token_hash,
                    AccessTokenRecord.revoked_at.is_(None),
                    AccessTokenRecord.expires_at > now,
                )
            )
            return None if record is None else self._to_user(record)

    def revoke_access_token(self, token_hash: str, revoked_at: datetime) -> None:
        """Revoke an active access token."""
        with self._session_factory.begin() as session:
            record: AccessTokenRecord | None = session.get(
                AccessTokenRecord, token_hash
            )
            if record is not None and record.revoked_at is None:
                record.revoked_at = revoked_at

    def add_oauth_state(
        self, state_hash: str, code_verifier: str, expires_at: datetime
    ) -> None:
        """Persist a short-lived OAuth state and PKCE verifier."""
        with self._session_factory.begin() as session:
            session.add(
                OAuthStateRecord(
                    state_hash=state_hash,
                    code_verifier=code_verifier,
                    expires_at=expires_at,
                )
            )

    def consume_oauth_state(self, state_hash: str, now: datetime) -> str | None:
        """Consume a matching unexpired OAuth state once."""
        with self._session_factory.begin() as session:
            record: OAuthStateRecord | None = session.get(OAuthStateRecord, state_hash)
            if record is None:
                return None
            verifier: str | None = (
                record.code_verifier if record.expires_at > now else None
            )
            session.delete(record)
            return verifier

    @staticmethod
    def _to_user(record: UserRecord) -> User:
        """Convert an ORM account record to its public model."""
        return User(
            user_id=record.user_id,
            email=record.email,
            role=record.role,
        )
