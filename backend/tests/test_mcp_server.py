from datetime import datetime

import pytest

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.repositories.database import Database
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
) -> None:
    data_service.add_ticket(sample_ticket)

    tickets: list[TicketToolResult] = mcp_server.list_tickets()

    assert len(tickets) == 1
    assert tickets[0]["issue"] == sample_ticket.issue
    assert tickets[0]["status"] == sample_ticket.status


def test_get_park_returns_park_by_id(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    parks: list[dict[str, str | int | float | None]] = mcp_server.list_parks()
    park_id: int = int(parks[0]["park_id"])  # type: ignore

    park: dict[str, str | int | float | None] = mcp_server.get_park(park_id)

    assert park["name"] == sample_park.name


def test_get_park_raises_for_unknown_id(mcp_server: ChiparkMcpServer) -> None:
    with pytest.raises(LookupError):
        mcp_server.get_park(999)


def test_list_parks_requires_active_data_service() -> None:
    mcp_server: ChiparkMcpServer = ChiparkMcpServer()

    with pytest.raises(RuntimeError, match="lifespan is not active"):
        mcp_server.list_parks()


def test_submit_ticket_creates_open_ticket(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "Broken bench",
    )

    assert ticket["status"] == TicketStatus.OPEN


def test_submit_ticket_escapes_issue(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "<script>alert('x')</script>",
    )

    assert ticket["issue"] == "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;"


def test_submit_ticket_uses_server_timestamp(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    request_started: datetime = datetime.now()

    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "Broken bench",
    )

    request_finished: datetime = datetime.now()
    filed_at: datetime = datetime.fromisoformat(str(ticket["file_date"]))
    assert request_started <= filed_at <= request_finished


def test_submit_ticket_preserves_estimated_hours(
    mcp_server: ChiparkMcpServer, sample_park: Park
) -> None:
    ticket: TicketToolResult = mcp_server.submit_ticket(
        sample_park.name,
        "Broken bench",
        estimated_hours=2.5,
    )

    assert ticket["estimated_hours"] == 2.5


def test_submit_ticket_rejects_unknown_park(
    mcp_server: ChiparkMcpServer,
) -> None:
    with pytest.raises(ValueError, match="Park 'Unknown Park' was not found"):
        mcp_server.submit_ticket("Unknown Park", "Broken bench")
