from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from ..models.notification import MAX_NOTIFICATIONS_PER_REQUEST, Notification
from ..models.user import User
from ..services.auth_dependencies import AuthDependencies
from ..services.data_service import DataService
from ..services.notification_stream import NotificationStream

router: APIRouter = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def get_notifications(
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_user)],
    limit: Annotated[
        int, Query(ge=1, le=MAX_NOTIFICATIONS_PER_REQUEST)
    ] = MAX_NOTIFICATIONS_PER_REQUEST,
) -> list[Notification]:
    """Return the authenticated user's newest notifications.

    Parameters
    ----------
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Authenticated notification recipient.
    limit : int, default=100
        Maximum number of notifications to return.

    Returns
    -------
    list[Notification]
        Notifications ordered newest first.
    """
    return data_service.get_notifications(user.user_id, limit)


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_user)],
) -> Notification:
    """Mark one of the authenticated user's notifications as read.

    Parameters
    ----------
    notification_id : int
        Identifier of the notification to mark as read.
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Authenticated notification recipient.

    Returns
    -------
    Notification
        Updated notification.

    Raises
    ------
    HTTPException
        If the notification does not belong to the authenticated user.
    """
    try:
        return data_service.mark_notification_read(user.user_id, notification_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/stream")
async def stream_notifications(
    request: Request,
    data_service: Annotated[DataService, Depends(DataService.get_default_service)],
    user: Annotated[User, Depends(AuthDependencies.require_user)],
    last_event_id_header: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Stream new notifications to the authenticated user using SSE.

    Parameters
    ----------
    data_service : DataService
        App-scoped service backed by the configured database.
    user : User
        Authenticated notification recipient.
    last_event_id_header : str or None, default=None
        Last event ID supplied by a reconnecting SSE client.

    Returns
    -------
    StreamingResponse
        Text event stream with automatic database polling.

    Raises
    ------
    HTTPException
        If the reconnect cursor is not a non-negative integer.
    """
    last_event_id: int | None = _parse_last_event_id(last_event_id_header)
    notification_stream: NotificationStream = NotificationStream(data_service)
    return StreamingResponse(
        notification_stream.events(
            request,
            user.user_id,
            last_event_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_last_event_id(value: str | None) -> int | None:
    """Parse and validate an optional SSE reconnect cursor.

    Parameters
    ----------
    value : str or None
        ``Last-Event-ID`` header value.

    Returns
    -------
    int or None
        Valid non-negative event ID, or ``None`` for a new connection.

    Raises
    ------
    HTTPException
        If the value is not a non-negative integer.
    """
    if value is None:
        return None
    try:
        last_event_id: int = int(value)
    except ValueError as error:
        raise HTTPException(
            status_code=400, detail="Last-Event-ID must be a non-negative integer."
        ) from error
    if last_event_id < 0:
        raise HTTPException(
            status_code=400, detail="Last-Event-ID must be a non-negative integer."
        )
    return last_event_id
