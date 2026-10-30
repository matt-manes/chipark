import pytest
from fastapi import FastAPI
from starlette.requests import Request

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.repositories.database import Database
from backend.services.data_service import DataService


def test_add_and_get_parks(database: Database, sample_park: Park) -> None:
    data_service: DataService = DataService(database)

    saved_park: Park = data_service.add_park(sample_park)

    assert data_service.get_parks() == [saved_park]


def test_add_parks(database: Database, sample_park: Park) -> None:
    data_service: DataService = DataService(database)
    second_park: Park = Park(
        park_no="P002",
        name="Second Park",
        street="456 Oak Street",
        zip_code="60602",
        acres="20",
        ward="2",
        park_class="COMMUNITY PARK",
        label="Second Park",
        lat=41.89,
        lon=-87.64,
    )

    data_service.add_parks([sample_park, second_park])

    parks: list[Park] = data_service.get_parks()

    assert parks[0].name == sample_park.name
    assert parks[1].name == second_park.name


def test_add_and_get_ticket(
    database: Database, sample_park: Park, sample_ticket: Ticket
) -> None:
    data_service: DataService = DataService(database)
    data_service.add_park(sample_park)

    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    assert data_service.get_ticket(saved_ticket.ticket_id) == saved_ticket


def test_get_tickets(
    database: Database, sample_park: Park, sample_ticket: Ticket
) -> None:
    data_service: DataService = DataService(database)
    data_service.add_park(sample_park)
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    assert data_service.get_tickets() == [saved_ticket]


def test_get_ticket_raises_for_missing_ticket(database: Database) -> None:
    data_service: DataService = DataService(database)

    with pytest.raises(LookupError, match="Ticket 42 was not found"):
        data_service.get_ticket(42)


def test_close_ticket(
    database: Database, sample_park: Park, sample_ticket: Ticket
) -> None:
    data_service: DataService = DataService(database)
    data_service.add_park(sample_park)
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    closed_ticket: Ticket = data_service.close_ticket(saved_ticket.ticket_id)

    assert closed_ticket.status is TicketStatus.CLOSED


def test_default_service_returns_service_from_app_state(
    database: Database,
) -> None:
    application: FastAPI = FastAPI()
    expected_service: DataService = DataService(database)
    application.state.data_service = expected_service
    request: Request = Request({"type": "http", "app": application})

    service: DataService = DataService.get_default_service(request)

    assert service is expected_service
