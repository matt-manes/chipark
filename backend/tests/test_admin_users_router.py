from fastapi.testclient import TestClient
from httpx2 import Response

from backend.models.ticket import TicketStatus
from backend.tools.config import Config


def _register_user(client: TestClient, email: str) -> tuple[int, str]:
    response: Response = client.post(
        "/auth/register",
        json={"email": email, "password": "a-secure-user-password"},
    )
    return response.json()["user"]["user_id"], response.json()["access_token"]


def test_admin_can_list_limited_user_details(api_client: TestClient) -> None:
    user_id: int
    user_id, _token = _register_user(api_client, "managed-user@example.com")

    response: Response = api_client.get("/admin/users")
    user: dict[str, object] = next(
        item for item in response.json() if item["user_id"] == user_id
    )

    assert response.status_code == 200
    assert user == {
        "user_id": user_id,
        "email": "managed-user@example.com",
        "role": "user",
        "is_active": True,
    }


def test_admin_can_promote_and_demote_user(api_client: TestClient) -> None:
    user_id: int
    user_id, _token = _register_user(api_client, "role-user@example.com")

    promoted: Response = api_client.patch(
        f"/admin/users/{user_id}/role", json={"role": "admin"}
    )
    demoted: Response = api_client.patch(
        f"/admin/users/{user_id}/role", json={"role": "user"}
    )

    assert promoted.json()["role"] == "admin"
    assert demoted.json()["role"] == "user"


def test_disabling_user_revokes_session_and_denies_login_and_registration(
    api_client: TestClient,
) -> None:
    user_id: int
    token: str
    user_id, token = _register_user(api_client, "disabled-user@example.com")

    disabled: Response = api_client.patch(
        f"/admin/users/{user_id}/status", json={"is_active": False}
    )
    current_user: Response = api_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    login: Response = api_client.post(
        "/auth/login",
        json={
            "email": "disabled-user@example.com",
            "password": "a-secure-user-password",
        },
    )
    registration: Response = api_client.post(
        "/auth/register",
        json={
            "email": "disabled-user@example.com",
            "password": "another-secure-password",
        },
    )

    assert disabled.json()["is_active"] is False
    assert current_user.status_code == 401
    assert login.status_code == 401
    assert registration.status_code == 409


def test_regular_user_cannot_access_admin_user_list(api_client: TestClient) -> None:
    _user_id: int
    token: str
    _user_id, token = _register_user(api_client, "regular-user@example.com")

    response: Response = api_client.get(
        "/admin/users", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_missing_admin_user_returns_not_found(api_client: TestClient) -> None:
    response: Response = api_client.get("/admin/users/999999")

    assert response.status_code == 404


def test_admin_can_get_user_details(api_client: TestClient) -> None:
    user_id: int
    user_id, _token = _register_user(api_client, "details-user@example.com")

    response: Response = api_client.get(f"/admin/users/{user_id}")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": user_id,
        "email": "details-user@example.com",
        "role": "user",
        "is_active": True,
    }


def test_admin_can_view_users_submitted_tickets(api_client: TestClient) -> None:
    user_id: int
    token: str
    user_id, token = _register_user(api_client, "ticket-user@example.com")
    submission: Response = api_client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={"park_name": "Sample Park", "issue": "Broken bench"},
    )

    response: Response = api_client.get(f"/admin/users/{user_id}/tickets")

    assert submission.status_code == 201
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["user_id"] == user_id
    assert response.json()[0]["status"] == TicketStatus.OPEN.value


def test_user_list_contains_bootstrap_admin(api_client: TestClient) -> None:
    response: Response = api_client.get("/admin/users")

    assert any(
        item["email"] == Config().CHIPARK_ADMIN_EMAIL for item in response.json()
    )
