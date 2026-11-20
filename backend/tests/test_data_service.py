from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from backend.clients.weatherapi_client import WeatherApiClient
from backend.models.conditions import Conditions
from backend.models.notification import Notification
from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus, TicketUpdate
from backend.models.user import User
from backend.repositories.conditions_repository import ConditionsRepository
from backend.repositories.database import Database
from backend.services import data_service as data_service_module
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


def _stub_weather_client(
    monkeypatch: pytest.MonkeyPatch,
    conditions: Conditions,
    ttl_seconds: int = 900,
) -> Mock:
    weather_client: Mock = Mock(spec=WeatherApiClient)
    weather_client.get_current_conditions.return_value = conditions
    monkeypatch.setattr(data_service_module, "WeatherApiClient", lambda: weather_client)
    monkeypatch.setattr(
        data_service_module,
        "Config",
        lambda: SimpleNamespace(CHIPARK_CONDITIONS_TTL=ttl_seconds),
    )
    return weather_client


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


def test_get_random_user_id_returns_database_user(
    database: Database, sample_user: User
) -> None:
    data_service: DataService = DataService(database)

    assert data_service.get_random_user_id() == sample_user.user_id


def test_get_random_user_id_returns_none_without_users(database: Database) -> None:
    data_service: DataService = DataService(database)

    assert data_service.get_random_user_id() is None


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


def test_get_conditions_fetches_and_caches_missing_entry(
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
    sample_park: Park,
    sample_conditions: Conditions,
) -> None:
    data_service: DataService = DataService(database)
    saved_park: Park = data_service.add_park(sample_park)
    conditions_repository: ConditionsRepository = ConditionsRepository(
        database.session_factory
    )
    weather_client: Mock = _stub_weather_client(monkeypatch, sample_conditions)

    result: Conditions | None = data_service.get_conditions(saved_park.park_id)

    assert result == sample_conditions
    assert conditions_repository.get_for_park(saved_park.park_id) == sample_conditions
    weather_client.get_current_conditions.assert_called_once_with(
        saved_park.lat, saved_park.lon
    )


def test_get_conditions_uses_fresh_cached_entry(
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
    sample_park: Park,
    sample_conditions: Conditions,
) -> None:
    data_service: DataService = DataService(database)
    saved_park: Park = data_service.add_park(sample_park)
    cached_conditions: Conditions = replace(
        sample_conditions, temp_f=61.0, condition="Rainy"
    )
    ConditionsRepository(database.session_factory).add(
        saved_park.park_id, cached_conditions
    )
    weather_client: Mock = _stub_weather_client(monkeypatch, sample_conditions)

    result: Conditions | None = data_service.get_conditions(saved_park.park_id)

    assert result == cached_conditions
    weather_client.get_current_conditions.assert_not_called()


def test_get_conditions_refreshes_expired_cached_entry(
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
    sample_park: Park,
    sample_conditions: Conditions,
) -> None:
    data_service: DataService = DataService(database)
    saved_park: Park = data_service.add_park(sample_park)
    expired_conditions: Conditions = replace(
        sample_conditions,
        last_updated=datetime.now(UTC) - timedelta(minutes=30),
    )
    conditions_repository: ConditionsRepository = ConditionsRepository(
        database.session_factory
    )
    conditions_repository.add(saved_park.park_id, expired_conditions)
    weather_client: Mock = _stub_weather_client(monkeypatch, sample_conditions)

    result: Conditions | None = data_service.get_conditions(saved_park.park_id)

    assert result == sample_conditions
    assert conditions_repository.get_for_park(saved_park.park_id) == sample_conditions
    weather_client.get_current_conditions.assert_called_once_with(
        saved_park.lat, saved_park.lon
    )


def test_get_conditions_raises_for_missing_park(
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
    sample_conditions: Conditions,
) -> None:
    data_service: DataService = DataService(database)
    weather_client: Mock = _stub_weather_client(monkeypatch, sample_conditions)

    with pytest.raises(LookupError, match="Park 42 was not found"):
        data_service.get_conditions(42)

    weather_client.get_current_conditions.assert_not_called()


def test_get_park_with_conditions_populates_conditions(
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
    sample_park: Park,
    sample_conditions: Conditions,
) -> None:
    data_service: DataService = DataService(database)
    saved_park: Park = data_service.add_park(sample_park)
    _stub_weather_client(monkeypatch, sample_conditions)

    park: Park = data_service.get_park_with_conditions(saved_park.park_id)

    assert park.conditions == sample_conditions


def test_get_park_leaves_conditions_unset(
    database: Database,
    sample_park: Park,
) -> None:
    data_service: DataService = DataService(database)
    saved_park: Park = data_service.add_park(sample_park)

    park: Park = data_service.get_park(saved_park.park_id)

    assert park.conditions is None


def test_default_service_returns_service_from_app_state(
    database: Database,
) -> None:
    application: FastAPI = FastAPI()
    expected_service: DataService = DataService(database)
    application.state.data_service = expected_service
    request: Request = Request({"type": "http", "app": application})

    service: DataService = DataService.get_default_service(request)

    assert service is expected_service
