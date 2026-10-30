from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from backend.app import app
from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.repositories.database import Database
from backend.services.data_service import DataService


@pytest.fixture
def data_service(database: Database, sample_park: Park) -> DataService:
    service: DataService = DataService(database)
    service.add_park(sample_park)
    return service


@pytest.fixture
def saved_ticket(data_service: DataService, sample_ticket: Ticket) -> Ticket:
    return data_service.add_ticket(sample_ticket)


@pytest.fixture
def api_client(data_service: DataService) -> Iterator[TestClient]:
    def provide_data_service() -> Iterator[DataService]:
        yield data_service

    app.dependency_overrides[DataService.get_default_service] = provide_data_service
    try:
        with TestClient(app) as client:
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
