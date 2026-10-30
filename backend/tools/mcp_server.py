from dataclasses import asdict
from datetime import datetime
from html import escape
from typing import ClassVar

from mcp.server import MCPServer
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.types import Receive, Scope, Send

from ..models.park import Park
from ..models.ticket import Ticket, TicketStatus
from ..services.data_service import DataService

ParkToolResult = dict[str, str | int | float | None]
TicketToolResult = dict[str, str | int | float | TicketStatus | None]


class McpAsgiApp:
    """Delegate ASGI requests to the MCP app active in the host lifespan."""

    def __init__(self) -> None:
        """Create an inactive MCP ASGI delegate."""
        self._application: Starlette | None = None

    def set_application(self, application: Starlette | None) -> None:
        """Set the active MCP application for the host lifespan."""
        self._application = application

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward an ASGI request to the active MCP application."""
        application: Starlette | None = self._application
        if application is None:
            raise RuntimeError("The Chipark MCP application is not running.")
        await application(scope, receive, send)


class ChiparkMcpServer:
    """Expose park and ticket operations through the Model Context Protocol."""

    TOOL_DESCRIPTIONS: ClassVar[dict[str, str]] = {
        "list_tools": "List the tools available on the Chipark MCP server.",
        "list_parks": "List all parks.",
        "list_tickets": "List all tickets.",
        "get_park": "Get a park by its database ID.",
        "submit_ticket": "Submit an open ticket for an existing park.",
    }

    def __init__(self) -> None:
        """Create the MCP server and register its tools."""
        self._data_service: DataService | None = None
        self._server: MCPServer = MCPServer("Chipark")
        self._server.tool()(self.list_tools)
        self._server.tool()(self.list_parks)
        self._server.tool()(self.list_tickets)
        self._server.tool()(self.get_park)
        self._server.tool()(self.submit_ticket)

    def asgi_app(self) -> Starlette:
        """
        Create the Streamable HTTP ASGI app for mounting in FastAPI.

        Returns
        -------
        Starlette
            MCP application exposing the Streamable HTTP endpoint.
        """
        return self._server.streamable_http_app()

    @property
    def session_manager(self) -> StreamableHTTPSessionManager:
        """Return the MCP session manager used by the host lifespan."""
        return self._server.session_manager

    def set_data_service(self, data_service: DataService | None) -> None:
        """
        Set the app-scoped data service available to registered tools.

        Parameters
        ----------
        data_service : DataService or None
            Active service, or ``None`` while the application is stopped.
        """
        self._data_service = data_service

    def list_tools(self) -> list[dict[str, str]]:
        """
        List the tools exposed by this Chipark MCP server.

        Returns
        -------
        list[dict[str, str]]
            Tool names and descriptions.
        """
        return [
            {"name": name, "description": description}
            for name, description in self.TOOL_DESCRIPTIONS.items()
        ]

    def list_parks(self) -> list[ParkToolResult]:
        """
        List parks stored in the database.

        Returns
        -------
        list[ParkToolResult]
            Park records ordered by database identifier.
        """
        data_service: DataService = self._require_data_service()
        parks: list[Park] = data_service.get_parks()
        return [self._park_to_result(park) for park in parks]

    def list_tickets(self) -> list[TicketToolResult]:
        """
        List tickets stored in the database.

        Returns
        -------
        list[TicketToolResult]
            Ticket records ordered by database identifier.
        """
        data_service: DataService = self._require_data_service()
        tickets: list[Ticket] = data_service.get_tickets()
        return [self._ticket_to_result(ticket) for ticket in tickets]

    def get_park(self, park_id: int) -> ParkToolResult:
        """
        Retrieve a park by its database identifier.

        Parameters
        ----------
        park_id : int
            Identifier of the park to retrieve.

        Returns
        -------
        ParkToolResult
            Matching park record.

        Raises
        ------
        LookupError
            If no park has the requested identifier.
        """
        data_service: DataService = self._require_data_service()
        park: Park = data_service.get_park(park_id)
        return self._park_to_result(park)

    def submit_ticket(
        self,
        park_name: str,
        issue: str,
        estimated_hours: float | None = None,
    ) -> TicketToolResult:
        """
        Submit an open ticket for a park that exists in the database.

        Parameters
        ----------
        park_name : str
            Exact name of an existing park.
        issue : str
            User-submitted issue description.
        estimated_hours : float or None, default=None
            Estimated repair duration, if known.

        Returns
        -------
        TicketToolResult
            Newly saved ticket.

        Raises
        ------
        ValueError
            If the park does not exist.
        """
        data_service: DataService = self._require_data_service()
        if not data_service.park_exists(park_name):
            raise ValueError(f"Park '{park_name}' was not found.")

        ticket: Ticket = Ticket(
            park_name=park_name,
            status=TicketStatus.OPEN,
            file_date=datetime.now(),
            estimated_hours=estimated_hours,
            issue=escape(issue),
        )
        saved_ticket: Ticket = data_service.add_ticket(ticket)
        return self._ticket_to_result(saved_ticket)

    def _require_data_service(self) -> DataService:
        """Return the active app-scoped service or raise if the app is stopped."""
        if self._data_service is None:
            raise RuntimeError("The Chipark application lifespan is not active.")
        return self._data_service

    @staticmethod
    def _park_to_result(park: Park) -> ParkToolResult:
        """
        Convert a park model to MCP-compatible structured data.

        Parameters
        ----------
        park : Park
            Park model to convert.

        Returns
        -------
        ParkToolResult
            Structured park fields.
        """
        return asdict(park)

    @staticmethod
    def _ticket_to_result(ticket: Ticket) -> TicketToolResult:
        """
        Convert a ticket model to MCP-compatible structured data.

        Parameters
        ----------
        ticket : Ticket
            Ticket model to convert.

        Returns
        -------
        TicketToolResult
            Structured ticket fields.
        """
        result: TicketToolResult = asdict(ticket)
        result["file_date"] = ticket.file_date.isoformat()
        return result
