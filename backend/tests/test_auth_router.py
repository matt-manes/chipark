from fastapi.testclient import TestClient
from httpx2 import Response


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
            "email": "admin@example.com",
            "password": "a-secure-admin-password",
        },
    )

    assert response.status_code == 409


def test_login_returns_unauthorized_for_invalid_credentials(
    api_client: TestClient,
) -> None:
    response: Response = api_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_logout_revokes_the_current_token(api_client: TestClient) -> None:
    login_response: Response = api_client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "a-secure-admin-password",
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
