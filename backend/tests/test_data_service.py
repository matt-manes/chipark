import pytest
from fastapi import FastAPI
from starlette.requests import Request

from backend.models.notification import Notification
from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus, TicketUpdate
from backend.models.user import User
from backend.repositories.database import Database
from backend.services.data_service import DataService


def _create_notifications(
    data_service: DataService,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
    issues: list[str],
) -> list[Notification]:
    data_service.add_park(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)
    for issue in issues:
        data_service.update_ticket(saved_ticket.ticket_id, TicketUpdate(issue=issue))
    return data_service.get_notifications(sample_user.user_id)


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


def test_update_ticket_changes_supplied_fields(
    database: Database, sample_park: Park, sample_ticket: Ticket
) -> None:
    data_service: DataService = DataService(database)
    data_service.add_park(sample_park)
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    updated_ticket: Ticket = data_service.update_ticket(
        saved_ticket.ticket_id, TicketUpdate(issue="Updated issue")
    )

    assert updated_ticket.issue == "Updated issue"


def test_delete_ticket_removes_ticket(
    database: Database, sample_park: Park, sample_ticket: Ticket
) -> None:
    data_service: DataService = DataService(database)
    data_service.add_park(sample_park)
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    data_service.delete_ticket(saved_ticket.ticket_id)

    with pytest.raises(LookupError, match="Ticket"):
        data_service.get_ticket(saved_ticket.ticket_id)


def test_get_notifications_after_returns_newer_notifications(
    database: Database,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    data_service: DataService = DataService(database)
    notifications: list[Notification] = _create_notifications(
        data_service,
        sample_park,
        sample_ticket,
        sample_user,
        ["First update", "Second update"],
    )

    result: list[Notification] = data_service.get_notifications_after(
        sample_user.user_id,
        min(notification.notification_id for notification in notifications),
    )

    assert len(result) == 1
    assert result[0].notification_id == max(
        notification.notification_id for notification in notifications
    )


def test_get_latest_notification_id_returns_latest_user_notification(
    database: Database,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    data_service: DataService = DataService(database)
    notifications: list[Notification] = _create_notifications(
        data_service,
        sample_park,
        sample_ticket,
        sample_user,
        ["First update", "Second update"],
    )

    latest_id: int = data_service.get_latest_notification_id(sample_user.user_id)

    assert latest_id == max(
        notification.notification_id for notification in notifications
    )


def test_get_latest_notification_id_returns_zero_without_notifications(
    database: Database, sample_user: User
) -> None:
    data_service: DataService = DataService(database)

    latest_id: int = data_service.get_latest_notification_id(sample_user.user_id)

    assert latest_id == 0


def test_mark_notification_read_returns_read_notification(
    database: Database,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    data_service: DataService = DataService(database)
    notifications: list[Notification] = _create_notifications(
        data_service, sample_park, sample_ticket, sample_user, ["Ticket updated"]
    )

    result: Notification = data_service.mark_notification_read(
        sample_user.user_id, notifications[0].notification_id
    )

    assert result.read_at is not None


def test_default_service_returns_service_from_app_state(
    database: Database,
) -> None:
    application: FastAPI = FastAPI()
    expected_service: DataService = DataService(database)
    application.state.data_service = expected_service
    request: Request = Request({"type": "http", "app": application})

    service: DataService = DataService.get_default_service(request)

    assert service is expected_service
