import asyncio
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request

from backend.models.notification import Notification, NotificationEventType
from backend.services import notification_stream
from backend.services.data_service import DataService
from backend.services.notification_stream import NotificationStream


def _read_first_event(events: AsyncGenerator[str, None]) -> str:
    async def read_and_close() -> str:
        try:
            return await anext(events)
        finally:
            await events.aclose()

    return asyncio.run(read_and_close())


def _read_events(events: AsyncGenerator[str, None], event_count: int) -> list[str]:
    async def read_and_close() -> list[str]:
        received_events: list[str] = []
        try:
            for _ in range(event_count):
                received_events.append(await anext(events))
            return received_events
        finally:
            await events.aclose()

    return asyncio.run(read_and_close())


def _drain_events(events: AsyncGenerator[str, None]) -> list[str]:
    async def read_and_close() -> list[str]:
        received_events: list[str] = []
        try:
            async for event in events:
                received_events.append(event)
            return received_events
        finally:
            await events.aclose()

    return asyncio.run(read_and_close())


@pytest.fixture
def sample_notification() -> Notification:
    return Notification(
        notification_id=11,
        event_type=NotificationEventType.TICKET_UPDATED,
        ticket_id=5,
        park_name="Sample Park",
        issue="Updated bench",
        created_at=datetime(2026, 11, 7, 12, 0),
        read_at=None,
    )


def test_events_starts_after_latest_notification_for_new_connection(
    sample_notification: Notification,
) -> None:
    data_service_mock: Mock = Mock(spec=DataService)
    data_service_mock.get_latest_notification_id.return_value = 10
    data_service_mock.get_notifications_after.return_value = [sample_notification]
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.return_value = False
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )
    events = stream.events(cast(Request, request_mock), user_id=7, last_event_id=None)

    frame: str = _read_first_event(events)

    data_service_mock.get_latest_notification_id.assert_called_once_with(7)
    data_service_mock.get_notifications_after.assert_called_once_with(7, 10, 100)
    assert frame.startswith("id: 11\nevent: ticket_updated\ndata: ")
    assert frame.endswith("\n\n")


def test_events_resumes_after_supplied_event_id(
    sample_notification: Notification,
) -> None:
    data_service_mock: Mock = Mock(spec=DataService)
    data_service_mock.get_notifications_after.return_value = [sample_notification]
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.return_value = False
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )
    events = stream.events(cast(Request, request_mock), user_id=7, last_event_id=9)

    frame: str = _read_first_event(events)

    data_service_mock.get_latest_notification_id.assert_not_called()
    data_service_mock.get_notifications_after.assert_called_once_with(7, 9, 100)
    assert frame.startswith("id: 11\nevent: ticket_updated\ndata: ")


def test_events_stops_when_client_is_disconnected() -> None:
    data_service_mock: Mock = Mock(spec=DataService)
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.return_value = True
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )
    events = stream.events(cast(Request, request_mock), user_id=7, last_event_id=0)

    with pytest.raises(StopAsyncIteration):
        _read_first_event(events)

    data_service_mock.get_notifications_after.assert_not_called()


def test_events_stops_if_client_disconnects_before_delivery(
    sample_notification: Notification,
) -> None:
    data_service_mock: Mock = Mock(spec=DataService)
    data_service_mock.get_notifications_after.return_value = [sample_notification]
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.side_effect = [False, True]
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )

    events: list[str] = _drain_events(
        stream.events(cast(Request, request_mock), user_id=7, last_event_id=0)
    )

    assert events == []


def test_events_emits_heartbeat_when_no_notifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_service_mock: Mock = Mock(spec=DataService)
    data_service_mock.get_notifications_after.return_value = []
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.side_effect = [False, True]
    monotonic_mock: Mock = Mock(side_effect=[0.0, 16.0])
    sleep_mock: AsyncMock = AsyncMock()
    monkeypatch.setattr(notification_stream, "monotonic", monotonic_mock)
    monkeypatch.setattr(notification_stream.asyncio, "sleep", sleep_mock)
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )

    events: list[str] = _drain_events(
        stream.events(cast(Request, request_mock), user_id=7, last_event_id=0)
    )

    assert events == [": keep-alive\n\n"]
    sleep_mock.assert_awaited_once_with(NotificationStream.POLL_INTERVAL_SECONDS)


def test_events_waits_between_empty_poll_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_service_mock: Mock = Mock(spec=DataService)
    data_service_mock.get_notifications_after.return_value = []
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.side_effect = [False, True]
    sleep_mock: AsyncMock = AsyncMock()
    monkeypatch.setattr(notification_stream.asyncio, "sleep", sleep_mock)
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )

    events: list[str] = _drain_events(
        stream.events(cast(Request, request_mock), user_id=7, last_event_id=0)
    )

    assert events == []
    sleep_mock.assert_awaited_once_with(NotificationStream.POLL_INTERVAL_SECONDS)


def test_events_continues_after_full_batch_with_advanced_cursor(
    sample_notification: Notification,
) -> None:
    first_batch: list[Notification] = [
        replace(sample_notification, notification_id=notification_id)
        for notification_id in range(1, NotificationStream.BATCH_SIZE + 1)
    ]
    next_notification: Notification = replace(
        sample_notification, notification_id=NotificationStream.BATCH_SIZE + 1
    )
    data_service_mock: Mock = Mock(spec=DataService)
    data_service_mock.get_notifications_after.side_effect = [
        first_batch,
        [next_notification],
    ]
    request_mock: AsyncMock = AsyncMock()
    request_mock.is_disconnected.side_effect = [False] * (
        NotificationStream.BATCH_SIZE + 3
    ) + [True]
    stream: NotificationStream = NotificationStream(
        cast(DataService, data_service_mock)
    )

    events: list[str] = _read_events(
        stream.events(cast(Request, request_mock), user_id=7, last_event_id=0),
        NotificationStream.BATCH_SIZE + 1,
    )

    assert len(events) == NotificationStream.BATCH_SIZE + 1
    assert data_service_mock.get_notifications_after.call_count == 2
    assert data_service_mock.get_notifications_after.call_args_list[1].args == (
        7,
        NotificationStream.BATCH_SIZE,
        NotificationStream.BATCH_SIZE,
    )
