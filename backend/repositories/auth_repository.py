from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.user import User, UserCredentials, UserRole
from .entities import AccessTokenRecord, OAuthStateRecord, UserRecord


class AuthRepository:
    """Persist authentication accounts and token records.

    Parameters
    ----------
    session_factory : sessionmaker[Session]
        Factory used to create database sessions.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Initialize the repository.

        Parameters
        ----------
        session_factory : sessionmaker[Session]
            Factory used to create database sessions.
        """
        self._session_factory: sessionmaker[Session] = session_factory

    def create_user(
        self,
        email: str,
        password_hash: str | None,
        google_subject: str | None = None,
    ) -> User:
        """Create a regular user account.

        Parameters
        ----------
        email : str
            Normalized email address for the account.
        password_hash : str or None
            Password hash, or ``None`` for an OAuth-only account.
        google_subject : str or None, default=None
            Google identity subject, when linking an OAuth account.

        Returns
        -------
        User
            The newly created account.
        """
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
        """Retrieve an account and its private credentials by email.

        Parameters
        ----------
        email : str
            Normalized email address to look up.

        Returns
        -------
        UserCredentials or None
            Account and credential data, or ``None`` if no account matches.
        """
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
        """Find the account linked to a Google identity.

        Parameters
        ----------
        google_subject : str
            Google identity subject identifier.

        Returns
        -------
        User or None
            Matching account, or ``None`` if no account is linked.
        """
        with self._session_factory() as session:
            record: UserRecord | None = session.scalar(
                select(UserRecord).where(UserRecord.google_subject == google_subject)
            )
            return None if record is None else self._to_user(record)

    def link_google_account(self, email: str, google_subject: str) -> User:
        """Link a verified Google identity to an email-matched account.

        Parameters
        ----------
        email : str
            Verified, normalized Google account email.
        google_subject : str
            Google identity subject identifier.

        Returns
        -------
        User
            The created or linked account.

        Raises
        ------
        ValueError
            If the email is already linked to a different Google identity.
        """
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
        """Create or promote the configured administrator account.

        Parameters
        ----------
        email : str
            Administrator email address.
        password_hash : str
            Password hash to assign to the administrator.

        Returns
        -------
        User
            The created or promoted administrator.
        """
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
        """Check whether an administrator account exists.

        Returns
        -------
        bool
            Whether the database contains an administrator.
        """
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
        """Persist a hashed bearer token.

        Parameters
        ----------
        token_hash : str
            SHA-256 digest of the bearer token.
        user_id : int
            Identifier of the token owner.
        expires_at : datetime
            Token expiration timestamp.
        """
        with self._session_factory.begin() as session:
            session.add(
                AccessTokenRecord(
                    token_hash=token_hash,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )

    def get_user_for_token(self, token_hash: str, now: datetime) -> User | None:
        """Look up the owner of an active bearer token.

        Parameters
        ----------
        token_hash : str
            SHA-256 digest of the token.
        now : datetime
            Current timestamp used to check token expiration.

        Returns
        -------
        User or None
            Token owner if the token is active, otherwise ``None``.
        """
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
        """Mark an active access token as revoked.

        Parameters
        ----------
        token_hash : str
            SHA-256 digest of the token to revoke.
        revoked_at : datetime
            Timestamp at which the token was revoked.
        """
        with self._session_factory.begin() as session:
            record: AccessTokenRecord | None = session.get(
                AccessTokenRecord, token_hash
            )
            if record is not None and record.revoked_at is None:
                record.revoked_at = revoked_at

    def add_oauth_state(
        self, state_hash: str, code_verifier: str, expires_at: datetime
    ) -> None:
        """Persist one-time OAuth state and its PKCE verifier.

        Parameters
        ----------
        state_hash : str
            SHA-256 digest of the OAuth state value.
        code_verifier : str
            PKCE verifier associated with the state.
        expires_at : datetime
            State expiration timestamp.
        """
        with self._session_factory.begin() as session:
            session.add(
                OAuthStateRecord(
                    state_hash=state_hash,
                    code_verifier=code_verifier,
                    expires_at=expires_at,
                )
            )

    def consume_oauth_state(self, state_hash: str, now: datetime) -> str | None:
        """Consume an OAuth state and return its verifier if still valid.

        Parameters
        ----------
        state_hash : str
            SHA-256 digest of the submitted OAuth state.
        now : datetime
            Current timestamp used to check state expiration.

        Returns
        -------
        str or None
            PKCE verifier for a valid state, otherwise ``None``.
        """
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
        """Convert an ORM account record to its public model.

        Parameters
        ----------
        record : UserRecord
            Persisted account record.

        Returns
        -------
        User
            Public account model without credential fields.
        """
        return User(
            user_id=record.user_id,
            email=record.email,
            role=record.role,
        )
