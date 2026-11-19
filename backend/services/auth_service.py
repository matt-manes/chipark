import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import SplitResult, urlsplit

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..models.user import AuthenticatedUser, User, UserCredentials, UserRole
from ..repositories.auth_repository import AuthRepository
from ..tools.config import Config
from .auth_errors import AuthenticationError
from .google_oauth import GoogleIdentity, GoogleOAuthClient


class PasswordHasher:
    """Hash and verify passwords with the standard-library scrypt primitive."""

    _COST: int = 2**8
    _BLOCK_SIZE: int = 8
    _PARALLELISM: int = 1
    _KEY_LENGTH: int = 64
    _SALT_LENGTH: int = 16

    def hash(self, password: str) -> str:
        """Create a salted scrypt hash.

        Parameters
        ----------
        password : str
            Plain-text password to hash.

        Returns
        -------
        str
            Encoded scrypt parameters, salt, and derived key.
        """
        salt: bytes = secrets.token_bytes(self._SALT_LENGTH)
        digest: bytes = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self._COST,
            r=self._BLOCK_SIZE,
            p=self._PARALLELISM,
            dklen=self._KEY_LENGTH,
        )
        return "$".join(
            (
                "scrypt",
                str(self._COST),
                str(self._BLOCK_SIZE),
                str(self._PARALLELISM),
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(digest).decode("ascii"),
            )
        )

    def verify(self, password: str, password_hash: str | None) -> bool:
        """Check a password against a stored scrypt hash.

        Parameters
        ----------
        password : str
            Plain-text password to verify.
        password_hash : str or None
            Encoded scrypt hash to compare against.

        Returns
        -------
        bool
            Whether the password matches the hash.
        """
        if password_hash is None:
            return False
        try:
            parts: list[str] = password_hash.split("$")
            if len(parts) != 6:
                return False
            algorithm: str = parts[0]
            cost_text: str = parts[1]
            block_text: str = parts[2]
            parallel_text: str = parts[3]
            salt_text: str = parts[4]
            digest_text: str = parts[5]
            if algorithm != "scrypt":
                return False
            cost: int = int(cost_text)
            block_size: int = int(block_text)
            parallelism: int = int(parallel_text)
            salt: bytes = base64.urlsafe_b64decode(salt_text)
            expected_digest: bytes = base64.urlsafe_b64decode(digest_text)
            actual_digest: bytes = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=cost,
                r=block_size,
                p=parallelism,
                dklen=len(expected_digest),
            )
        except (ValueError, TypeError, UnicodeError):
            return False
        return hmac.compare_digest(actual_digest, expected_digest)


class AuthService:
    """Manage accounts, Google OAuth, and revocable bearer tokens.

    Parameters
    ----------
    session_factory : sessionmaker[Session]
        Factory used by the authentication repository.
    """

    _TOKEN_LIFETIME: timedelta = timedelta(hours=24)
    _OAUTH_STATE_LIFETIME: timedelta = timedelta(minutes=5)
    _MAX_PASSWORD_LENGTH: int = 128
    _MIN_PASSWORD_LENGTH: int = 6

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Initialize the service and its authentication helpers.

        Parameters
        ----------
        session_factory : sessionmaker[Session]
            Factory used by the authentication repository.
        """
        self._repository: AuthRepository = AuthRepository(session_factory)
        self._password_hasher: PasswordHasher = PasswordHasher()
        self._google_oauth_client: GoogleOAuthClient = GoogleOAuthClient()
        self._dummy_password_hash: str = self._password_hasher.hash(
            "unavailable-account-password"
        )

    def register(self, email: str, password: str) -> AuthenticatedUser:
        """Create a regular account and issue a bearer token.

        Parameters
        ----------
        email : str
            Email address for the new account.
        password : str
            Password to hash and store.

        Returns
        -------
        AuthenticatedUser
            New account and its access token.

        Raises
        ------
        AuthenticationError
            If the email is invalid, the password is outside allowed bounds, or
            the account already exists.
        """
        normalized_email: str = self._normalize_email(email)
        self._validate_password(password)
        try:
            user: User = self._repository.create_user(
                normalized_email, self._password_hasher.hash(password)
            )
        except IntegrityError as error:
            raise AuthenticationError(
                "An account with this email already exists."
            ) from error
        return self._issue_token(user)

    def login(self, email: str, password: str) -> AuthenticatedUser:
        """Authenticate an account and issue a bearer token.

        Parameters
        ----------
        email : str
            Email address of the account.
        password : str
            Password to verify.

        Returns
        -------
        AuthenticatedUser
            Authenticated account and its access token.

        Raises
        ------
        AuthenticationError
            If the email or password is incorrect.
        """
        normalized_email: str = self._normalize_email(email)
        credentials: UserCredentials | None = self._repository.get_credentials_by_email(
            normalized_email
        )
        stored_hash: str | None = (
            self._dummy_password_hash
            if credentials is None or credentials.password_hash is None
            else credentials.password_hash
        )
        password_matches: bool = self._password_hasher.verify(password, stored_hash)
        if (
            credentials is None
            or not password_matches
            or not credentials.user.is_active
        ):
            raise AuthenticationError("Email or password is incorrect.")
        return self._issue_token(credentials.user)

    def authenticate_token(self, token: str) -> User | None:
        """Resolve the owner of an active bearer token.

        Parameters
        ----------
        token : str
            Opaque bearer token supplied by the caller.

        Returns
        -------
        User or None
            Token owner if the token is active and unexpired.
        """
        return self._repository.get_user_for_token(
            self._hash_token(token), self._utc_now()
        )

    def authenticate_authorization_header(
        self, authorization: str | None
    ) -> User | None:
        """Authenticate a bearer token from an authorization header.

        Parameters
        ----------
        authorization : str or None
            Authorization header value.

        Returns
        -------
        User or None
            Authenticated account, or ``None`` for an invalid or absent token.
        """
        if authorization is None:
            return None
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.casefold() != "bearer" or not token.strip():
            return None
        return self.authenticate_token(token.strip())

    def logout(self, token: str) -> None:
        """Revoke a bearer token.

        Parameters
        ----------
        token : str
            Opaque bearer token to revoke.
        """
        self._repository.revoke_access_token(self._hash_token(token), self._utc_now())

    def get_users(self) -> list[User]:
        """Return all user accounts for administrator management."""
        return self._repository.get_all_users()

    def get_user(self, user_id: int) -> User:
        """Return one account or raise when the identifier is unknown."""
        user: User | None = self._repository.get_user(user_id)
        if user is None:
            raise LookupError(f"User {user_id} was not found")
        return user

    def update_user_role(self, user_id: int, role: UserRole) -> User:
        """Change an account's role."""
        return self._repository.update_user_role(user_id, role)

    def set_user_active(self, user_id: int, is_active: bool) -> User:
        """Enable or disable an account and revoke its tokens if disabled."""
        return self._repository.set_user_active(user_id, is_active, self._utc_now())

    def update_profile(
        self,
        user_id: int,
        email: str | None,
        current_password: str | None,
        new_password: str | None,
    ) -> User:
        """Update the email and/or password for a password-based account.

        Parameters
        ----------
        user_id : int
            Authenticated account identifier.
        email : str or None
            New email address, if requested.
        current_password : str or None
            Existing password required when changing the password.
        new_password : str or None
            Replacement password, if requested.

        Returns
        -------
        User
            Updated public account details.

        Raises
        ------
        AuthenticationError
            If the account uses Google OAuth, the current password is invalid,
            or the request contains no changes.
        IntegrityError
            If the new email is already in use.
        """
        if email is None and new_password is None:
            raise AuthenticationError("At least one profile field must be provided.")

        credentials: UserCredentials | None = (
            self._repository.get_credentials_by_user_id(user_id)
        )
        if credentials is None:
            raise AuthenticationError("The account was not found.")
        if credentials.google_subject is not None or credentials.password_hash is None:
            raise AuthenticationError(
                "Google-linked accounts cannot update credentials here."
            )

        password_hash: str | None = None
        if new_password is not None:
            self._validate_password(new_password)
            if current_password is None or not self._password_hasher.verify(
                current_password, credentials.password_hash
            ):
                raise AuthenticationError("The current password is incorrect.")
            password_hash = self._password_hasher.hash(new_password)

        normalized_email: str | None = (
            None if email is None else self._normalize_email(email)
        )
        try:
            return self._repository.update_profile(
                user_id, normalized_email, password_hash
            )
        except IntegrityError as error:
            raise AuthenticationError(
                "An account with this email already exists."
            ) from error

    def bootstrap_admin(self, email: str | None, password: str | None) -> User | None:
        """Create or promote the configured administrator account.

        Parameters
        ----------
        email : str or None
            Administrator email from the environment.
        password : str or None
            Administrator password from the environment.

        Returns
        -------
        User or None
            Created or promoted administrator, or ``None`` when an administrator
            exists and no bootstrap credentials were supplied.

        Raises
        ------
        AuthenticationError
            If credentials are incomplete or no administrator exists.
        """
        if email is None and password is None:
            if self._repository.has_admin():
                return None
            raise AuthenticationError(
                "Set CHIPARK_ADMIN_EMAIL and CHIPARK_ADMIN_PASSWORD to bootstrap "
                "the first administrator."
            )
        if email is None or password is None:
            raise AuthenticationError(
                "CHIPARK_ADMIN_EMAIL and CHIPARK_ADMIN_PASSWORD must both be set."
            )
        self._validate_password(password)
        return self._repository.ensure_admin(
            self._normalize_email(email), self._password_hasher.hash(password)
        )

    def begin_google_login(self) -> str:
        """Create a Google authorization URL with one-time state and PKCE.

        Returns
        -------
        str
            Authorization URL for redirecting the user to Google.

        Raises
        ------
        AuthenticationError
            If required Google client configuration is missing.
        """
        state: str = secrets.token_urlsafe(32)
        code_verifier: str = secrets.token_urlsafe(64)
        authorization_url: str = self._google_oauth_client.authorization_url(
            state, code_verifier
        )
        self._repository.add_oauth_state(
            self._hash_token(state),
            code_verifier,
            self._utc_now() + self._OAUTH_STATE_LIFETIME,
        )
        return authorization_url

    async def complete_google_login(
        self, authorization_code: str, state: str
    ) -> AuthenticatedUser:
        """Exchange a Google code and authenticate its verified account.

        Parameters
        ----------
        authorization_code : str
            Authorization code returned by Google.
        state : str
            One-time OAuth state from the authorization request.

        Returns
        -------
        AuthenticatedUser
            Verified account and issued bearer token.

        Raises
        ------
        AuthenticationError
            If state is invalid or expired, the Google exchange fails, or account
            linking cannot be completed.
        """
        code_verifier: str | None = self._repository.consume_oauth_state(
            self._hash_token(state), self._utc_now()
        )
        if code_verifier is None:
            raise AuthenticationError("The Google OAuth state is invalid or expired.")

        identity: GoogleIdentity = (
            await self._google_oauth_client.get_verified_identity(
                authorization_code, code_verifier
            )
        )
        email: str = self._normalize_email(identity.email)
        user: User | None = self._repository.get_user_by_google_subject(
            identity.subject
        )
        if user is None:
            try:
                user = self._repository.link_google_account(email, identity.subject)
            except IntegrityError as error:
                raise AuthenticationError(
                    "This Google account could not be linked."
                ) from error
            except ValueError as error:
                raise AuthenticationError(str(error)) from error
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")
        return self._issue_token(user)

    @staticmethod
    def frontend_oauth_redirect_url() -> str:
        """Return the configured frontend OAuth redirect URL.

        Returns
        -------
        str
            Valid HTTP(S) frontend redirect URL.

        Raises
        ------
        AuthenticationError
            If the configured URL does not use HTTP or HTTPS.
        """
        redirect_url: str = Config().CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL
        parsed_url: SplitResult = urlsplit(redirect_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise AuthenticationError(
                "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL must be an HTTP(S) URL."
            )
        return redirect_url

    def _issue_token(self, user: User) -> AuthenticatedUser:
        """Create and persist an opaque bearer token.

        Parameters
        ----------
        user : User
            Account that will own the token.

        Returns
        -------
        AuthenticatedUser
            Account and newly issued token with its expiry timestamp.
        """
        token: str = secrets.token_urlsafe(32)
        expires_at: datetime = self._utc_now() + self._TOKEN_LIFETIME
        self._repository.add_access_token(
            self._hash_token(token), user.user_id, expires_at
        )
        return AuthenticatedUser(
            user=user,
            access_token=token,
            expires_at=expires_at.replace(tzinfo=UTC),
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a bearer token or OAuth state value.

        Parameters
        ----------
        token : str
            Secret value to hash.

        Returns
        -------
        str
            Hex-encoded SHA-256 digest.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Normalize an email address for account lookup.

        Parameters
        ----------
        email : str
            Email address to normalize.

        Returns
        -------
        str
            Trimmed, case-folded email address.

        Raises
        ------
        AuthenticationError
            If the address does not have a valid basic email structure.
        """
        normalized_email: str = email.strip().casefold()
        local_part, separator, domain = normalized_email.partition("@")
        if (
            not separator
            or not local_part
            or "." not in domain
            or domain.startswith(".")
            or domain.endswith(".")
        ):
            raise AuthenticationError("A valid email address is required.")
        return normalized_email

    @classmethod
    def _validate_password(cls, password: str) -> None:
        """Validate password length.

        Parameters
        ----------
        password : str
            Password to validate.

        Raises
        ------
        AuthenticationError
            If the password is shorter than the minimum or longer than the
            maximum supported length.
        """
        if not cls._MIN_PASSWORD_LENGTH <= len(password) <= cls._MAX_PASSWORD_LENGTH:
            raise AuthenticationError(
                f"Passwords must be between {cls._MIN_PASSWORD_LENGTH} and "
                f"{cls._MAX_PASSWORD_LENGTH} characters."
            )

    @staticmethod
    def _utc_now() -> datetime:
        """Return the current UTC time as a naive datetime.

        Returns
        -------
        datetime
            Current UTC timestamp without timezone information for SQLite.
        """
        return datetime.now(UTC).replace(tzinfo=None)
