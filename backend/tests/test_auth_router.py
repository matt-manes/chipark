from fastapi.testclient import TestClient
from httpx2 import Response

from backend.tools.config import Config


def test_registration_creates_user_and_returns_bearer_token(
    api_client: TestClient,
) -> None:
    response: Response = api_client.post(
        "/auth/register",
        json={
            "email": "new-user@example.com",
            "password": "a-secure-user-password",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "new-user@example.com"
    assert response.json()["user"]["role"] == "user"
    assert response.json()["access_token"]


def test_registration_returns_conflict_for_existing_email(
    api_client: TestClient,
) -> None:
    response: Response = api_client.post(
        "/auth/register",
        json={
            "email": Config().CHIPARK_ADMIN_EMAIL,
            "password": Config().CHIPARK_ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 409


def test_login_returns_unauthorized_for_invalid_credentials(
    api_client: TestClient,
) -> None:
    response: Response = api_client.post(
        "/auth/login",
        json={"email": Config().CHIPARK_ADMIN_EMAIL, "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_logout_revokes_the_current_token(api_client: TestClient) -> None:
    login_response: Response = api_client.post(
        "/auth/login",
        json={
            "email": Config().CHIPARK_ADMIN_EMAIL,
            "password": Config().CHIPARK_ADMIN_PASSWORD,
        },
    )
    token: str = login_response.json()["access_token"]

    logout_response: Response = api_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    current_user_response: Response = api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 204
    assert current_user_response.status_code == 401


def test_profile_update_changes_email(api_client: TestClient) -> None:
    response: Response = api_client.patch(
        "/auth/me", json={"email": "updated-admin@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "updated-admin@example.com"
    assert response.json()["password_login_enabled"] is True
    assert response.json()["google_login_enabled"] is False


def test_profile_update_requires_current_password_for_password_change(
    api_client: TestClient,
) -> None:
    response: Response = api_client.patch(
        "/auth/me", json={"new_password": "another-secure-password"}
    )

    assert response.status_code == 400
    assert response.json()["detail"][0]["msg"] == "The current password is incorrect."


def test_profile_update_changes_password(api_client: TestClient) -> None:
    response: Response = api_client.patch(
        "/auth/me",
        json={
            "current_password": Config().CHIPARK_ADMIN_PASSWORD,
            "new_password": "another-secure-password",
        },
    )
    login_response: Response = api_client.post(
        "/auth/login",
        json={
            "email": Config().CHIPARK_ADMIN_EMAIL,
            "password": "another-secure-password",
        },
    )

    assert response.status_code == 200
    assert login_response.status_code == 200


def test_profile_update_rejects_empty_changes(api_client: TestClient) -> None:
    response: Response = api_client.patch("/auth/me", json={})

    assert response.status_code == 400
    assert (
        response.json()["detail"][0]["msg"]
        == "At least one profile field must be provided."
    )


def test_cors_allows_configured_frontend_origin(api_client: TestClient) -> None:
    response: Response = api_client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
