import json

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from backend.models.park import Park
from backend.models.ticket import Ticket
from backend.models.user import AuthenticatedUser
from backend.repositories.database import Database
from backend.services.auth_service import AuthService
from backend.services.data_service import DataService
from backend.tools.config import Config


@pytest.fixture
def mcp_headers(api_client: TestClient) -> dict[str, str]:
    api_client.headers.pop("Authorization", None)
    headers: dict[str, str] = {
        "Host": "localhost:8000",
        "Accept": "application/json, text/event-stream",
    }
    response: Response = api_client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        },
    )
    assert response.status_code == 200
    headers["Mcp-Session-Id"] = response.headers["mcp-session-id"]
    headers["Mcp-Protocol-Version"] = "2025-03-26"
    response = api_client.post(
        "/mcp",
        headers=headers,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert response.status_code == 202
    return headers


@pytest.fixture
def mcp_admin_headers(
    api_client: TestClient, mcp_headers: dict[str, str]
) -> dict[str, str]:
    config: Config = Config()
    response: Response = api_client.post(
        "/auth/login",
        json={
            "email": config.CHIPARK_ADMIN_EMAIL,
            "password": config.CHIPARK_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return {**mcp_headers, "Authorization": f"Bearer {token}"}


def _call_tool(
    client: TestClient,
    headers: dict[str, str],
    name: str,
    arguments: dict[str, object],
) -> dict[str, object]:
    """Call an MCP tool and decode its response event."""
    response: Response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert response.status_code == 200
    data: str = next(
        line.removeprefix("data:").strip()
        for line in response.text.splitlines()
        if line.startswith("data:")
    )
    result: dict[str, object] = json.loads(data)["result"]
    return result


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("submit_ticket", {"park_name": "Sample Park", "issue": "Broken bench"}),
        ("close_ticket", {"ticket_id": 1}),
        ("edit_ticket", {"ticket_id": 1, "issue": "Broken bench"}),
        ("delete_ticket", {"ticket_id": 1}),
    ],
)
@pytest.mark.parametrize("authorization", [None, "Bearer invalid-token"])
def test_ticket_write_reports_missing_or_invalid_bearer_token(
    api_client: TestClient,
    mcp_headers: dict[str, str],
    name: str,
    arguments: dict[str, object],
    authorization: str | None,
) -> None:
    headers: dict[str, str] = mcp_headers.copy()
    if authorization is not None:
        headers["Authorization"] = authorization

    result: dict[str, object] = _call_tool(api_client, headers, name, arguments)

    assert result == {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Error executing tool {name}: "
                    "A valid bearer token is required for this MCP tool."
                ),
            }
        ],
        "isError": True,
    }


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("get_park", {"park_id": 999}, "Park 999 was not found"),
        (
            "submit_ticket",
            {"park_name": "Unknown Park", "issue": "Broken bench"},
            "Park 'Unknown Park' was not found.",
        ),
        ("close_ticket", {"ticket_id": 999}, "Ticket 999 was not found"),
        (
            "edit_ticket",
            {"ticket_id": 999, "issue": "Broken bench"},
            "Ticket 999 was not found",
        ),
        ("delete_ticket", {"ticket_id": 999}, "Ticket 999 was not found"),
        (
            "edit_ticket",
            {"ticket_id": 999},
            "At least one editable ticket field is required.",
        ),
        (
            "edit_ticket",
            {"ticket_id": 999, "estimated_hours": 1, "clear_estimated_hours": True},
            "Specify an estimated value or clear it, but not both.",
        ),
    ],
)
def test_tool_reports_expected_client_error(
    api_client: TestClient,
    mcp_admin_headers: dict[str, str],
    name: str,
    arguments: dict[str, object],
    message: str,
) -> None:
    result: dict[str, object] = _call_tool(
        api_client, mcp_admin_headers, name, arguments
    )

    assert result == {
        "content": [
            {"type": "text", "text": f"Error executing tool {name}: {message}"}
        ],
        "isError": True,
    }


def test_edit_ticket_reports_repository_validation_error(
    api_client: TestClient,
    mcp_admin_headers: dict[str, str],
    saved_ticket: Ticket,
) -> None:
    result: dict[str, object] = _call_tool(
        api_client,
        mcp_admin_headers,
        "edit_ticket",
        {"ticket_id": saved_ticket.ticket_id, "issue": ""},
    )

    assert result == {
        "content": [
            {
                "type": "text",
                "text": "Error executing tool edit_ticket: A ticket issue cannot be empty.",
            }
        ],
        "isError": True,
    }


def test_tool_masks_unexpected_error(
    api_client: TestClient,
    mcp_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_service: DataService, _park_id: int) -> Park:
        raise RuntimeError("private exception details")

    monkeypatch.setattr(DataService, "get_park", fail)

    result: dict[str, object] = _call_tool(
        api_client, mcp_headers, "get_park", {"park_id": 1}
    )

    assert result == {
        "content": [{"type": "text", "text": "Error executing tool get_park"}],
        "isError": True,
    }


def test_administrator_tool_reports_insufficient_privileges(
    api_client: TestClient,
    mcp_headers: dict[str, str],
    database: Database,
) -> None:
    auth_service: AuthService = AuthService(database.session_factory)
    user: AuthenticatedUser = auth_service.register(
        "mcp-member@example.com", "a-secure-password"
    )
    headers: dict[str, str] = {
        **mcp_headers,
        "Authorization": f"Bearer {user.access_token}",
    }

    result: dict[str, object] = _call_tool(
        api_client, headers, "close_ticket", {"ticket_id": 1}
    )

    assert result == {
        "content": [
            {
                "type": "text",
                "text": (
                    "Error executing tool close_ticket: "
                    "Administrator privileges are required."
                ),
            }
        ],
        "isError": True,
    }
