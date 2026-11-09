from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from starlette.requests import Request

from backend.models.park import Park
from backend.services.notification_stream import NotificationStream


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
