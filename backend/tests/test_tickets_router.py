from datetime import datetime

from fastapi.testclient import TestClient
from httpx2 import Response

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus


def test_get_tickets_returns_all_tickets(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.get("/tickets")

    assert response.status_code == 200
    assert response.json()[0]["ticket_id"] == saved_ticket.ticket_id


def test_get_ticket_returns_ticket_by_id(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.get(f"/tickets/{saved_ticket.ticket_id}")

    assert response.status_code == 200
    assert response.json()["issue"] == saved_ticket.issue


def test_get_ticket_returns_404_for_missing_ticket(api_client: TestClient) -> None:
    response: Response = api_client.get("/tickets/999")

    assert response.status_code == 404


def test_ticket_update_is_available_as_notification(
    api_client: TestClient, sample_park: Park
) -> None:
    ticket_response: Response = api_client.post(
        "/tickets",
        json={"park_name": sample_park.name, "issue": "Broken bench"},
    )
    ticket_id: int = ticket_response.json()["ticket_id"]

    update_response: Response = api_client.patch(
        f"/tickets/{ticket_id}", json={"issue": "Updated bench"}
    )
    notification_response: Response = api_client.get("/notifications")

    assert update_response.status_code == 200
    assert notification_response.status_code == 200
    notification: dict[str, object] = notification_response.json()[0]
    assert notification["event_type"] == "ticket_updated"
    assert notification["ticket_id"] == ticket_id
    assert notification["issue"] == "Updated bench"


def test_add_ticket_defaults_status_and_escapes_issue(
    api_client: TestClient, sample_park: Park
) -> None:
    request_started: datetime = datetime.now()
    response: Response = api_client.post(
        "/tickets",
        json={
            "park_name": sample_park.name,
            "estimated_hours": 2.5,
            "issue": "<script>alert('x')</script>",
        },
    )
    request_finished: datetime = datetime.now()

    assert response.status_code == 201
    assert response.json()["status"] == TicketStatus.OPEN.value
    filed_at: datetime = datetime.fromisoformat(response.json()["file_date"])
    assert request_started <= filed_at <= request_finished
    assert (
        response.json()["issue"] == "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;"
    )
    current_user_response: Response = api_client.get("/auth/me")
    assert response.json()["user_id"] == current_user_response.json()["user_id"]


def test_add_ticket_requires_login(api_client: TestClient, sample_park: Park) -> None:
    response: Response = api_client.post(
        "/tickets",
        headers={"Authorization": ""},
        json={"park_name": sample_park.name, "issue": "Broken bench"},
    )

    assert response.status_code == 401


def test_add_ticket_rejects_unknown_park(api_client: TestClient) -> None:
    response: Response = api_client.post(
        "/tickets",
        json={
            "park_name": "Unknown Park",
            "issue": "Broken bench",
        },
    )

    assert response.status_code == 422


def test_close_ticket_updates_status(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.patch(f"/tickets/{saved_ticket.ticket_id}/close")

    assert response.status_code == 200
    assert response.json()["status"] == TicketStatus.CLOSED.value


def test_close_ticket_returns_404_for_missing_ticket(api_client: TestClient) -> None:
    response: Response = api_client.patch("/tickets/999/close")

    assert response.status_code == 404


def test_regular_user_cannot_close_ticket(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    registration: Response = api_client.post(
        "/auth/register",
        json={
            "email": "member@example.com",
            "password": "a-secure-user-password",
        },
    )
    user_token: str = registration.json()["access_token"]

    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}/close",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


def test_regular_user_cannot_edit_ticket(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    registration: Response = api_client.post(
        "/auth/register",
        json={
            "email": "editor@example.com",
            "password": "a-secure-user-password",
        },
    )
    user_token: str = registration.json()["access_token"]

    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"issue": "Unauthorized edit"},
    )

    assert response.status_code == 403


def test_regular_user_cannot_delete_ticket(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    registration: Response = api_client.post(
        "/auth/register",
        json={
            "email": "deleter@example.com",
            "password": "a-secure-user-password",
        },
    )
    user_token: str = registration.json()["access_token"]

    response: Response = api_client.delete(
        f"/tickets/{saved_ticket.ticket_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


def test_admin_can_update_ticket(api_client: TestClient, saved_ticket: Ticket) -> None:
    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}",
        json={"issue": "Updated issue"},
    )

    assert response.status_code == 200
    assert response.json()["issue"] == "Updated issue"


def test_admin_cannot_update_ticket_park(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}",
        json={"park_name": "Different Park"},
    )

    assert response.status_code == 422


def test_admin_update_returns_404_for_missing_ticket(api_client: TestClient) -> None:
    response: Response = api_client.patch(
        "/tickets/999",
        json={"issue": "Updated issue"},
    )

    assert response.status_code == 404


def test_admin_update_returns_422_for_empty_issue(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}",
        json={"issue": ""},
    )

    assert response.status_code == 422


def test_admin_update_returns_422_for_empty_update(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}",
        json={},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "At least one field is required."


def test_admin_update_returns_422_for_null_issue(
    api_client: TestClient, saved_ticket: Ticket
) -> None:
    response: Response = api_client.patch(
        f"/tickets/{saved_ticket.ticket_id}",
        json={"issue": None},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Ticket issue cannot be null."


def test_admin_can_delete_ticket(api_client: TestClient, saved_ticket: Ticket) -> None:
    response: Response = api_client.delete(f"/tickets/{saved_ticket.ticket_id}")

    assert response.status_code == 204


def test_admin_delete_returns_404_for_missing_ticket(api_client: TestClient) -> None:
    response: Response = api_client.delete("/tickets/999")

    assert response.status_code == 404
