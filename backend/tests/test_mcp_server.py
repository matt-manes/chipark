from datetime import datetime
from typing import cast

import pytest
from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.session import ServerSession
from starlette.applications import Starlette
from starlette.requests import Request

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.models.user import AuthenticatedUser
from backend.repositories.database import Database
from backend.services.auth_service import AuthService
from backend.services.data_service import DataService
from backend.tools.mcp_server import ChiparkMcpServer, TicketToolResult


@pytest.fixture
def data_service(database: Database, sample_park: Park) -> DataService:
    data_service: DataService = DataService(database)
    data_service.add_park(sample_park)
    return data_service


@pytest.fixture
def mcp_server(data_service: DataService) -> ChiparkMcpServer:
    server: ChiparkMcpServer = ChiparkMcpServer()
    server.set_data_service(data_service)
    return server


@pytest.fixture
def auth_service(database: Database) -> AuthService:
    return AuthService(database.session_factory)


@pytest.fixture
def mcp_user_context(auth_service: AuthService) -> Context:
    authenticated_user: AuthenticatedUser = auth_service.register(
        "member@example.com", "a-secure-password"
    )
    return _create_context(auth_service, authenticated_user.access_token)


@pytest.fixture
def unauthenticated_context(auth_service: AuthService) -> Context:
    return _create_context(auth_service, None)


@pytest.fixture
def administrator_context(auth_service: AuthService) -> Context:
    auth_service.bootstrap_admin("admin@example.com", "a-secure-admin-password")
    authenticated_admin: AuthenticatedUser = auth_service.login(
        "admin@example.com", "a-secure-admin-password"
    )
    return _create_context(auth_service, authenticated_admin.access_token)


@pytest.fixture
def owned_mcp_ticket(
    data_service: DataService, sample_ticket: Ticket, auth_service: AuthService
) -> Ticket:
    owner: AuthenticatedUser = auth_service.register(
        "ticket-owner@example.com", "a-secure-password"
    )
    sample_ticket.user_id = owner.user.user_id
    return data_service.add_ticket(sample_ticket)


def _create_context(auth_service: AuthService, token: str | None) -> Context:
    """Create an MCP request context with an optional bearer credential.

    Parameters
    ----------
    auth_service : AuthService
        Authentication service used by the simulated request.
    token : str or None
        Bearer token to attach to the request, or ``None`` for no credential.

    Returns
    -------
    Context
        MCP context containing the constructed HTTP request.
    """
    mcp_application: Starlette = Starlette()
    mcp_application.state.auth_service = auth_service
    headers: list[tuple[bytes, bytes]] = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode("ascii")))
    request: Request = Request(
        {
            "type": "http",
            "app": mcp_application,
            "headers": headers,
        }
    )
    request_context: ServerRequestContext = ServerRequestContext(
        session=cast(ServerSession, None),
        lifespan_context={},
        protocol_version="2025-03-26",
        method="tools/call",
        request=request,
    )
    return Context(request_context=request_context)


def test_list_tools_returns_registered_tool_descriptions(
    mcp_server: ChiparkMcpServer,
) -> None:
    tools: list[dict[str, str]] = mcp_server.list_tools()

    assert [tool["name"] for tool in tools] == [
        "list_tools",
        "list_parks",
        "list_tickets",
        "get_park",
        "submit_ticket",
        "close_ticket",
        "edit_ticket",
        "delete_ticket",
    ]
    assert all(tool["description"] for tool in tools)


def test_list_parks_returns_saved_parks(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    parks: list[dict[str, str | int | float | None]] = mcp_server.list_parks()

    assert len(parks) == 1
    assert parks[0]["name"] == sample_park.name


def test_list_parks_allows_missing_address_fields(
    mcp_server: ChiparkMcpServer, data_service: DataService
) -> None:
    park: Park = Park(
        park_no="P003",
        name="Park Without Address",
        street=None,
        zip_code=None,
        acres="1",
        ward="1",
        park_class="NEIGHBORHOOD PARK",
        label="Park Without Address",
        lat=41.88,
        lon=-87.63,
    )
    data_service.add_park(park)

    parks: list[dict[str, str | int | float | None]] = mcp_server.list_parks()

    assert parks[1]["street"] is None
    assert parks[1]["zip_code"] is None


def test_list_tickets_returns_saved_tickets(
    mcp_server: ChiparkMcpServer,
    data_service: DataService,
    sample_ticket: Ticket,
    unauthenticated_context: Context,
) -> None:
    data_service.add_ticket(sample_ticket)

    tickets: list[TicketToolResult] = mcp_server.list_tickets(unauthenticated_context)

    assert len(tickets) == 1
    assert tickets[0]["issue"] == sample_ticket.issue
    assert tickets[0]["status"] == sample_ticket.status


def test_anonymous_mcp_ticket_list_hides_user_id(
    mcp_server: ChiparkMcpServer,
    owned_mcp_ticket: Ticket,
    unauthenticated_context: Context,
) -> None:
    tickets: list[TicketToolResult] = mcp_server.list_tickets(unauthenticated_context)

    assert tickets[0]["user_id"] is None


def test_regular_user_mcp_ticket_list_hides_user_id(
    mcp_server: ChiparkMcpServer,
    owned_mcp_ticket: Ticket,
    mcp_user_context: Context,
) -> None:
    tickets: list[TicketToolResult] = mcp_server.list_tickets(mcp_user_context)

    assert tickets[0]["user_id"] is None


def test_admin_mcp_ticket_list_includes_user_id(
    mcp_server: ChiparkMcpServer,
    owned_mcp_ticket: Ticket,
    administrator_context: Context,
) -> None:
    tickets: list[TicketToolResult] = mcp_server.list_tickets(administrator_context)

    assert tickets[0]["user_id"] == owned_mcp_ticket.user_id


def test_get_park_returns_park_by_id(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    parks: list[dict[str, str | int | float | None]] = mcp_server.list_parks()
    park_id_value: str | int | float | None = parks[0]["park_id"]
    assert isinstance(park_id_value, int)

    park: dict[str, str | int | float | None] = mcp_server.get_park(park_id_value)

    assert park["name"] == sample_park.name


def test_get_park_raises_for_unknown_id(mcp_server: ChiparkMcpServer) -> None:
    with pytest.raises(ToolError, match="Park 999 was not found"):
        mcp_server.get_park(999)


def test_list_parks_requires_active_data_service() -> None:
    mcp_server: ChiparkMcpServer = ChiparkMcpServer()

    with pytest.raises(RuntimeError, match="lifespan is not active"):
        mcp_server.list_parks()


def test_submit_ticket_creates_open_ticket(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    mcp_user_context: Context,
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "Broken bench",
        ctx=mcp_user_context,
    )

    assert ticket["status"] == TicketStatus.OPEN


def test_regular_user_mcp_submission_hides_user_id(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    mcp_user_context: Context,
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name, "Broken bench", ctx=mcp_user_context
    )

    assert ticket["user_id"] is None


def test_admin_mcp_submission_includes_user_id(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    administrator_context: Context,
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name, "Broken bench", ctx=administrator_context
    )

    assert ticket["user_id"] is not None


def test_submit_ticket_escapes_issue(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    mcp_user_context: Context,
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "<script>alert('x')</script>",
        ctx=mcp_user_context,
    )

    assert ticket["issue"] == "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;"


def test_submit_ticket_uses_server_timestamp(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    mcp_user_context: Context,
) -> None:
    request_started: datetime = datetime.now()

    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "Broken bench",
        ctx=mcp_user_context,
    )

    request_finished: datetime = datetime.now()
    filed_at: datetime = datetime.fromisoformat(str(ticket["file_date"]))
    assert request_started <= filed_at <= request_finished


def test_submit_ticket_preserves_estimated_hours(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    mcp_user_context: Context,
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "Broken bench",
        ctx=mcp_user_context,
        estimated_hours=2.5,
    )

    assert ticket["estimated_hours"] == 2.5


def test_submit_ticket_rejects_unknown_park(
    mcp_server: ChiparkMcpServer,
    mcp_user_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Park 'Unknown Park' was not found"):
        mcp_server.submit_ticket("Unknown Park", "Broken bench", ctx=mcp_user_context)


def test_submit_ticket_requires_authentication(
    mcp_server: ChiparkMcpServer,
    sample_park: Park,
    unauthenticated_context: Context,
) -> None:
    with pytest.raises(ToolError, match="valid bearer token"):
        mcp_server.submit_ticket(
            sample_park.name, "Broken bench", ctx=unauthenticated_context
        )


def test_submit_ticket_rejects_non_http_request_context(
    mcp_server: ChiparkMcpServer,
    mcp_user_context: Context,
) -> None:
    mcp_user_context.request_context.request = object()

    with pytest.raises(ToolError, match="bearer token is required"):
        mcp_server.submit_ticket("Sample Park", "Broken bench", ctx=mcp_user_context)


def test_close_ticket_rejects_regular_user(
    mcp_server: ChiparkMcpServer,
    mcp_user_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Administrator privileges"):
        mcp_server.close_ticket(1, ctx=mcp_user_context)


def test_close_ticket_raises_for_missing_ticket(
    mcp_server: ChiparkMcpServer,
    administrator_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Ticket 1 was not found"):
        mcp_server.close_ticket(1, ctx=administrator_context)


def test_edit_ticket_rejects_regular_user(
    mcp_server: ChiparkMcpServer,
    mcp_user_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Administrator privileges"):
        mcp_server.edit_ticket(1, ctx=mcp_user_context, issue="Changed issue")


def test_edit_ticket_requires_at_least_one_field(
    mcp_server: ChiparkMcpServer,
    administrator_context: Context,
) -> None:
    with pytest.raises(ToolError, match="At least one editable"):
        mcp_server.edit_ticket(1, ctx=administrator_context)


def test_edit_ticket_rejects_conflicting_estimate_updates(
    mcp_server: ChiparkMcpServer,
    administrator_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Specify an estimated value or clear it"):
        mcp_server.edit_ticket(
            1,
            ctx=administrator_context,
            estimated_hours=1.5,
            clear_estimated_hours=True,
        )


def test_edit_ticket_raises_for_missing_ticket(
    mcp_server: ChiparkMcpServer,
    administrator_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Ticket 1 was not found"):
        mcp_server.edit_ticket(1, ctx=administrator_context, issue="Updated issue")


def test_edit_ticket_rejects_empty_issue(
    mcp_server: ChiparkMcpServer,
    data_service: DataService,
    sample_ticket: Ticket,
    administrator_context: Context,
) -> None:
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    with pytest.raises(ToolError, match="issue cannot be empty"):
        mcp_server.edit_ticket(
            saved_ticket.ticket_id,
            ctx=administrator_context,
            issue="",
        )


def test_admin_can_close_ticket(
    mcp_server: ChiparkMcpServer,
    data_service: DataService,
    sample_ticket: Ticket,
    administrator_context: Context,
) -> None:
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    closed_ticket: TicketToolResult = mcp_server.close_ticket(
        saved_ticket.ticket_id, ctx=administrator_context
    )

    assert closed_ticket["status"] == TicketStatus.CLOSED


def test_admin_can_edit_ticket(
    mcp_server: ChiparkMcpServer,
    data_service: DataService,
    sample_ticket: Ticket,
    administrator_context: Context,
) -> None:
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    updated_ticket: TicketToolResult = mcp_server.edit_ticket(
        saved_ticket.ticket_id,
        ctx=administrator_context,
        issue="Updated issue",
    )

    assert updated_ticket["issue"] == "Updated issue"


def test_admin_can_clear_ticket_estimate(
    mcp_server: ChiparkMcpServer,
    data_service: DataService,
    sample_ticket: Ticket,
    administrator_context: Context,
) -> None:
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    updated_ticket: TicketToolResult = mcp_server.edit_ticket(
        saved_ticket.ticket_id,
        ctx=administrator_context,
        clear_estimated_hours=True,
    )

    assert updated_ticket["estimated_hours"] is None


def test_admin_can_delete_ticket(
    mcp_server: ChiparkMcpServer,
    data_service: DataService,
    sample_ticket: Ticket,
    administrator_context: Context,
) -> None:
    saved_ticket: Ticket = data_service.add_ticket(sample_ticket)

    result: dict[str, bool] = mcp_server.delete_ticket(
        saved_ticket.ticket_id, ctx=administrator_context
    )

    assert result == {"deleted": True}


def test_admin_delete_raises_for_missing_ticket(
    mcp_server: ChiparkMcpServer,
    administrator_context: Context,
) -> None:
    with pytest.raises(ToolError, match="Ticket 1 was not found"):
        mcp_server.delete_ticket(1, ctx=administrator_context)
