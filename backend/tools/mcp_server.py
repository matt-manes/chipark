from dataclasses import asdict
from datetime import datetime
from html import escape
from typing import ClassVar

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.types import Receive, Scope, Send

from ..models.park import Park
from ..models.ticket import Ticket, TicketStatus, TicketUpdate
from ..models.user import User, UserRole
from ..services.auth_service import AuthService
from ..services.data_service import DataService

ParkToolResult = dict[str, str | int | float | None]
TicketToolResult = dict[str, str | int | float | TicketStatus | None]


class McpAsgiApp:
    """Delegate ASGI requests to the MCP app active in the host lifespan."""

    def __init__(self) -> None:
        """Initialize an MCP ASGI delegate without an active application."""
        self._application: Starlette | None = None

    def set_application(self, application: Starlette | None) -> None:
        """Set the active application.

        Parameters
        ----------
        application : Starlette or None
            MCP application to delegate requests to, or ``None`` while stopped.
        """
        self._application = application

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward an ASGI request to the active MCP application.

        Parameters
        ----------
        scope : Scope
            ASGI connection scope.
        receive : Receive
            ASGI receive callable.
        send : Send
            ASGI send callable.

        Raises
        ------
        RuntimeError
            If the host lifespan has not activated the MCP application.
        """
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
        "submit_ticket": (
            "Submit a ticket for an existing park using an authenticated account."
        ),
        "close_ticket": "Close an existing ticket. Requires an administrator account.",
        "edit_ticket": (
            "Edit estimated hours or issue on an existing ticket. "
            "Requires an administrator account."
        ),
        "delete_ticket": "Delete an existing ticket. Requires an administrator account.",
    }

    def __init__(self) -> None:
        """Initialize the MCP server and register its tools."""
        self._data_service: DataService | None = None
        self._server: MCPServer = MCPServer("Chipark")
        self._server.tool()(self.list_tools)
        self._server.tool()(self.list_parks)
        self._server.tool()(self.list_tickets)
        self._server.tool()(self.get_park)
        self._server.tool()(self.submit_ticket)
        self._server.tool()(self.close_ticket)
        self._server.tool()(self.edit_ticket)
        self._server.tool()(self.delete_ticket)

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
        """Return the MCP session manager used by the host lifespan.

        Returns
        -------
        StreamableHTTPSessionManager
            Session manager associated with the MCP server.
        """
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
        ctx: Context,
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
            If the request is unauthenticated or the park does not exist.
        """
        user: User = self._require_mcp_user(ctx)
        data_service: DataService = self._require_data_service()
        if not data_service.park_exists(park_name):
            raise ValueError(f"Park '{park_name}' was not found.")

        ticket: Ticket = Ticket(
            park_name=park_name,
            status=TicketStatus.OPEN,
            file_date=datetime.now(),
            estimated_hours=estimated_hours,
            issue=escape(issue),
            user_id=user.user_id,
        )
        saved_ticket: Ticket = data_service.add_ticket(ticket)
        return self._ticket_to_result(saved_ticket)

    def close_ticket(self, ticket_id: int, ctx: Context) -> TicketToolResult:
        """Close a ticket after verifying administrator privileges.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to close.
        ctx : Context
            MCP request context containing the caller's authorization header.

        Returns
        -------
        TicketToolResult
            Updated ticket with closed status.

        Raises
        ------
        ValueError
            If the caller is not an administrator or the ticket does not exist.
        """
        self._require_mcp_admin(ctx)
        try:
            ticket: Ticket = self._require_data_service().close_ticket(ticket_id)
        except LookupError as error:
            raise ValueError(str(error)) from error
        return self._ticket_to_result(ticket)

    def edit_ticket(
        self,
        ticket_id: int,
        ctx: Context,
        estimated_hours: float | None = None,
        issue: str | None = None,
        clear_estimated_hours: bool = False,
    ) -> TicketToolResult:
        """Edit ticket details after verifying administrator privileges.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to update.
        ctx : Context
            MCP request context containing the caller's authorization header.
        estimated_hours : float or None, default=None
            Updated work estimate, when supplied.
        issue : str or None, default=None
            Updated issue description, when supplied.
        clear_estimated_hours : bool, default=False
            Whether to clear the existing work estimate.

        Returns
        -------
        TicketToolResult
            Updated ticket.

        Raises
        ------
        ValueError
            If the caller is not an administrator, the update is empty or
            conflicting, or the ticket does not exist.
        """
        self._require_mcp_admin(ctx)
        data_service: DataService = self._require_data_service()
        updates: dict[str, object] = {}
        if estimated_hours is not None:
            if clear_estimated_hours:
                raise ValueError(
                    "Specify an estimated value or clear it, but not both."
                )
            updates["estimated_hours"] = estimated_hours
        elif clear_estimated_hours:
            updates["estimated_hours"] = None
        if issue is not None:
            updates["issue"] = escape(issue)
        if not updates:
            raise ValueError("At least one editable ticket field is required.")
        try:
            ticket: Ticket = data_service.update_ticket(
                ticket_id, TicketUpdate.model_validate(updates)
            )
        except LookupError as error:
            raise ValueError(str(error)) from error
        return self._ticket_to_result(ticket)

    def delete_ticket(self, ticket_id: int, ctx: Context) -> dict[str, bool]:
        """Delete a ticket after verifying administrator privileges.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to delete.
        ctx : Context
            MCP request context containing the caller's authorization header.

        Returns
        -------
        dict[str, bool]
            Confirmation that the ticket was deleted.

        Raises
        ------
        ValueError
            If the caller is not an administrator or the ticket does not exist.
        """
        self._require_mcp_admin(ctx)
        try:
            self._require_data_service().delete_ticket(ticket_id)
        except LookupError as error:
            raise ValueError(str(error)) from error
        return {"deleted": True}

    def _require_data_service(self) -> DataService:
        """Return the active app-scoped data service.

        Returns
        -------
        DataService
            Service configured by the host application's lifespan.

        Raises
        ------
        RuntimeError
            If the host application is stopped.
        """
        if self._data_service is None:
            raise RuntimeError("The Chipark application lifespan is not active.")
        return self._data_service

    def _require_mcp_user(self, context: Context) -> User:
        """Authenticate the user making the current MCP request.

        Parameters
        ----------
        context : Context
            MCP request context with the underlying HTTP request.

        Returns
        -------
        User
            Account identified by the valid bearer token.

        Raises
        ------
        TypeError
            If the context does not contain an HTTP request.
        ValueError
            If the request has no valid bearer token.
        """
        request: object = context.request_context.request
        if not isinstance(request, Request):
            raise TypeError("A bearer token is required for this MCP tool.")
        auth_service: AuthService = request.app.state.auth_service
        user: User | None = auth_service.authenticate_authorization_header(
            request.headers.get("authorization")
        )
        if user is None:
            raise ValueError("A valid bearer token is required for this MCP tool.")
        return user

    def _require_mcp_admin(self, context: Context) -> User:
        """Authenticate the MCP request and require an administrator.

        Parameters
        ----------
        context : Context
            MCP request context with the underlying HTTP request.

        Returns
        -------
        User
            Authenticated administrator account.

        Raises
        ------
        TypeError
            If the context does not contain an HTTP request.
        ValueError
            If the request is unauthenticated or the account is not an admin.
        """
        user: User = self._require_mcp_user(context)
        if user.role is not UserRole.ADMIN:
            raise ValueError("Administrator privileges are required.")
        return user

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
