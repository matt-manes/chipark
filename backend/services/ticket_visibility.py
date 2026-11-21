from dataclasses import replace

from fastapi import Response

from ..models.ticket import Ticket
from ..models.user import User, UserRole


class TicketVisibility:
    """Apply ticket field visibility for the requesting account."""

    @staticmethod
    def for_user(ticket: Ticket, user: User | None) -> Ticket:
        """Return a ticket with its owner hidden from non-administrators."""
        if user and user.role is UserRole.ADMIN:
            return ticket
        return replace(ticket, user_id=None)

    @staticmethod
    def prevent_caching(response: Response) -> None:
        """Prevent caches from sharing role-dependent ticket responses."""
        response.headers["Cache-Control"] = "private, no-store"
