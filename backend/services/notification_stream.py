import asyncio
import json
from collections.abc import AsyncGenerator
from time import monotonic

from fastapi.encoders import jsonable_encoder
from starlette.requests import Request

from ..models.notification import Notification
from .data_service import DataService


class NotificationStream:
    """Poll persisted notifications and encode them as server-sent events."""

    POLL_INTERVAL_SECONDS: float = 10.0
    HEARTBEAT_INTERVAL_SECONDS: float = 15.0
    BATCH_SIZE: int = 100

    def __init__(self, data_service: DataService) -> None:
        """Create a stream backed by the application data service.

        Parameters
        ----------
        data_service : DataService
            Service used to query persisted notifications.
        """
        self._data_service: DataService = data_service

    async def events(
        self, request: Request, user_id: int, last_event_id: int | None
    ) -> AsyncGenerator[str, None]:
        """Yield SSE frames for a user's notifications.

        Parameters
        ----------
        request : Request
            Request monitored for client disconnects.
        user_id : int
            Authenticated notification recipient.
        last_event_id : int or None
            Last event ID supplied by the client when reconnecting.
        """
        if last_event_id is None:
            cursor: int = await asyncio.to_thread(
                self._data_service.get_latest_notification_id, user_id
            )
        else:
            cursor = last_event_id

        last_heartbeat: float = monotonic()
        while not await request.is_disconnected():
            notifications: list[Notification] = await asyncio.to_thread(
                self._data_service.get_notifications_after,
                user_id,
                cursor,
                self.BATCH_SIZE,
            )
            for notification in notifications:
                if await request.is_disconnected():
                    return
                yield self._format_event(notification)
                cursor = notification.notification_id
                last_heartbeat = monotonic()

            current_time: float = monotonic()
            if current_time - last_heartbeat >= self.HEARTBEAT_INTERVAL_SECONDS:
                yield ": keep-alive\n\n"
                last_heartbeat = current_time

            if len(notifications) == self.BATCH_SIZE:
                continue
            await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

    @staticmethod
    def _format_event(notification: Notification) -> str:
        """Encode one notification as a standards-compliant SSE frame.

        Parameters
        ----------
        notification : Notification
            Notification to encode.

        Returns
        -------
        str
            SSE event frame containing its ID, event type, and JSON data.
        """
        data: str = json.dumps(jsonable_encoder(notification), separators=(",", ":"))
        return (
            f"id: {notification.notification_id}\n"
            f"event: {notification.event_type.value}\n"
            f"data: {data}\n\n"
        )
