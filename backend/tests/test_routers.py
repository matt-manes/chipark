from collections.abc import AsyncIterator, Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from starlette.requests import Request

from backend.app import app
from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.repositories.database import Database
from backend.repositories.database_factory import DatabaseFactory
from backend.services.data_service import DataService
from backend.services.notification_stream import NotificationStream


@pytest.fixture
def data_service(database: Database, sample_park: Park) -> DataService:
    service: DataService = DataService(database)
    service.add_park(sample_park)
    return service


@pytest.fixture
def saved_ticket(data_service: DataService, sample_ticket: Ticket) -> Ticket:
    return data_service.add_ticket(sample_ticket)


@pytest.fixture
def api_client(
    data_service: DataService,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setattr(
        DatabaseFactory,
        "get_database",
        staticmethod(lambda database_type: database),  # type: ignore
    )
    monkeypatch.setenv("CHIPARK_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("CHIPARK_ADMIN_PASSWORD", "a-secure-admin-password")

    def provide_data_service() -> Iterator[DataService]:
        yield data_service

    app.dependency_overrides[DataService.get_default_service] = provide_data_service
    try:
        with TestClient(app) as client:
            login_response: Response = client.post(
                "/auth/login",
                json={
                    "email": "admin@example.com",
                    "password": "a-secure-admin-password",
                },
            )
            assert login_response.status_code == 200
            client.headers["Authorization"] = (
                f"Bearer {login_response.json()['access_token']}"
            )
            yield client
    finally:
        app.dependency_overrides.pop(DataService.get_default_service, None)


def test_get_parks_returns_all_parks(api_client: TestClient, sample_park: Park) -> None:
    response: Response = api_client.get("/parks")

    assert response.status_code == 200
    assert response.json()[0]["name"] == sample_park.name


def test_get_park_returns_park_by_id(
    api_client: TestClient, data_service: DataService, sample_park: Park
) -> None:
    saved_park: Park = data_service.get_parks()[0]

    response: Response = api_client.get(f"/parks/{saved_park.park_id}")

    assert response.status_code == 200
    assert response.json()["name"] == sample_park.name


def test_get_park_returns_404_for_missing_park(api_client: TestClient) -> None:
    response: Response = api_client.get("/parks/999")

    assert response.status_code == 404


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


def test_mark_notification_read_returns_updated_notification(
    api_client: TestClient, sample_park: Park
) -> None:
    ticket_response: Response = api_client.post(
        "/tickets",
        json={"park_name": sample_park.name, "issue": "Broken bench"},
    )
    ticket_id: int = ticket_response.json()["ticket_id"]
    api_client.patch(f"/tickets/{ticket_id}", json={"issue": "Updated bench"})
    notification_response: Response = api_client.get("/notifications")
    notification_id: int = notification_response.json()[0]["notification_id"]

    response: Response = api_client.patch(f"/notifications/{notification_id}/read")

    assert response.status_code == 200
    assert response.json()["read_at"] is not None


def test_mark_notification_read_returns_404_for_missing_notification(
    api_client: TestClient,
) -> None:
    response: Response = api_client.patch("/notifications/999/read")

    assert response.status_code == 404


def test_stream_notifications_returns_sse_response(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_cursors: list[int | None] = []

    async def provide_one_event(
        _stream: NotificationStream,
        _request: Request,
        _user_id: int,
        last_event_id: int | None,
    ) -> AsyncIterator[str]:
        received_cursors.append(last_event_id)
        yield "id: 5\nevent: ticket_updated\ndata: {}\n\n"

    monkeypatch.setattr(NotificationStream, "events", provide_one_event)

    response: Response = api_client.get(
        "/notifications/stream", headers={"Last-Event-ID": "4"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == "id: 5\nevent: ticket_updated\ndata: {}\n\n"
    assert received_cursors == [4]


def test_stream_notifications_rejects_invalid_event_id(
    api_client: TestClient,
) -> None:
    response: Response = api_client.get(
        "/notifications/stream", headers={"Last-Event-ID": "invalid"}
    )

    assert response.status_code == 400


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
