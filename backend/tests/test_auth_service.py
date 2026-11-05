from urllib.parse import parse_qs, urlsplit

import pytest

from backend.models.user import AuthenticatedUser, UserRole
from backend.repositories.database import Database
from backend.services.auth_service import AuthenticationError, AuthService


@pytest.fixture
def auth_service(database: Database) -> AuthService:
    return AuthService(database.session_factory)


def test_register_normalizes_email_and_creates_regular_account(
    auth_service: AuthService,
) -> None:
    result: AuthenticatedUser = auth_service.register(
        "Member@Example.com", "a-secure-user-password"
    )

    assert result.user.email == "member@example.com"
    assert result.user.role is UserRole.USER
    assert auth_service.authenticate_token(result.access_token) == result.user


def test_register_rejects_duplicate_email(auth_service: AuthService) -> None:
    auth_service.register("member@example.com", "a-secure-user-password")

    with pytest.raises(AuthenticationError, match="already exists"):
        auth_service.register("MEMBER@example.com", "another-secure-password")


def test_login_rejects_invalid_password(auth_service: AuthService) -> None:
    auth_service.register("member@example.com", "a-secure-user-password")

    with pytest.raises(AuthenticationError, match="incorrect"):
        auth_service.login("member@example.com", "wrong-password")


def test_logout_revokes_the_access_token(auth_service: AuthService) -> None:
    authenticated_user: AuthenticatedUser = auth_service.register(
        "member@example.com", "a-secure-user-password"
    )

    auth_service.logout(authenticated_user.access_token)

    assert auth_service.authenticate_token(authenticated_user.access_token) is None


def test_bootstrap_admin_creates_an_administrator(
    auth_service: AuthService,
) -> None:
    administrator = auth_service.bootstrap_admin(
        "admin@example.com", "a-secure-admin-password"
    )

    assert administrator is not None
    assert administrator.role is UserRole.ADMIN


def test_bootstrap_admin_requires_credentials_on_empty_database(
    auth_service: AuthService,
) -> None:
    with pytest.raises(AuthenticationError, match="CHIPARK_ADMIN_EMAIL"):
        auth_service.bootstrap_admin(None, None)


def test_google_login_url_uses_pkce(
    auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHIPARK_GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv(
        "CHIPARK_GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback",
    )

    authorization_url: str = auth_service.begin_google_login()
    query: dict[str, list[str]] = parse_qs(urlsplit(authorization_url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
