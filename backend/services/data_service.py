from collections.abc import Sequence
from typing import Self

from starlette.requests import Request

from ..models.notification import MAX_NOTIFICATIONS_PER_REQUEST, Notification
from ..models.park import Park
from ..models.ticket import Ticket, TicketUpdate
from ..repositories import (
    Database,
    NotificationRepository,
    ParkRepository,
    TicketRepository,
)


class DataService:
    """Expose park and ticket operations through their repositories."""

    @classmethod
    def get_default_service(cls, request: Request) -> Self:
        """
        Return the service created during the application lifespan.

        Parameters
        ----------
        request : Request
            Current request, used to access application state.

        Returns
        -------
        Self
            Application-scoped service backed by the configured database.

        Notes
        -----
        The application lifespan owns the service and closes it at shutdown.
        """
        data_service: Self = request.app.state.data_service
        return data_service

    def __init__(self, database: Database) -> None:
        """
        Create a service backed by the supplied database.

        Parameters
        ----------
        database : Database
            Database providing the repositories' SQLAlchemy sessions.
        """
        self._database: Database = database
        self._park_repository: ParkRepository = ParkRepository(
            self._database.session_factory
        )
        self._ticket_repository: TicketRepository = TicketRepository(
            self._database.session_factory
        )
        self._notification_repository: NotificationRepository = NotificationRepository(
            self._database.session_factory
        )

    def add_park(self, park: Park) -> Park:
        """
        Add a park to the database.

        Parameters
        ----------
        park : Park
            Park to persist.

        Returns
        -------
        Park
            Persisted park model.
        """
        return self._park_repository.add(park)

    def add_parks(self, parks: Sequence[Park]) -> None:
        """
        Add each park in a sequence to the database.

        Parameters
        ----------
        parks : Sequence[Park]
            Parks to persist.
        """
        for park in parks:
            self.add_park(park)

    def get_parks(self) -> list[Park]:
        """
        Retrieve all parks from the database.

        Returns
        -------
        list[Park]
            Persisted parks in database identifier order.
        """
        return self._park_repository.get_all()

    def get_park(self, park_id: int) -> Park:
        """
        Retrieve a park by its database identifier.

        Parameters
        ----------
        park_id : int
            Identifier of the park to retrieve.

        Returns
        -------
        Park
            Matching persisted park.

        Raises
        ------
        LookupError
            If no park has the requested identifier.
        """
        return self._park_repository.get(park_id)

    def park_exists(self, park_name: str) -> bool:
        """
        Check whether a park with the given name exists.

        Parameters
        ----------
        park_name : str
            Name of the park to find.

        Returns
        -------
        bool
            Whether a matching park exists.
        """
        return self._park_repository.park_exists(park_name)

    def get_ticket(self, ticket_id: int) -> Ticket:
        """
        Retrieve a ticket by its database identifier.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to retrieve.

        Returns
        -------
        Ticket
            Matching persisted ticket.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        return self._ticket_repository.get(ticket_id)

    def get_tickets(self) -> list[Ticket]:
        """
        Retrieve all tickets from the database.

        Returns
        -------
        list[Ticket]
            Persisted tickets in database identifier order.
        """
        return self._ticket_repository.get_all()

    def add_ticket(self, ticket: Ticket) -> Ticket:
        """
        Add a ticket to the database.

        Parameters
        ----------
        ticket : Ticket
            Ticket to persist.

        Returns
        -------
        Ticket
            Persisted ticket model.
        """
        return self._ticket_repository.add(ticket)

    def close_ticket(self, ticket_id: int) -> Ticket:
        """
        Mark a ticket as closed.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to close.

        Returns
        -------
        Ticket
            Updated ticket with closed status.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        return self._ticket_repository.close(ticket_id)

    def update_ticket(self, ticket_id: int, changes: TicketUpdate) -> Ticket:
        """Update editable fields on an existing ticket.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to update.
        changes : TicketUpdate
            Validated fields to change.

        Returns
        -------
        Ticket
            Updated ticket.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        ValueError
            If a non-nullable editable field is set to ``None``.
        """
        return self._ticket_repository.update(ticket_id, changes)

    def delete_ticket(self, ticket_id: int) -> None:
        """Delete an existing ticket.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to delete.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        self._ticket_repository.delete(ticket_id)

    def get_notifications(
        self, user_id: int, limit: int = MAX_NOTIFICATIONS_PER_REQUEST
    ) -> list[Notification]:
        """Return the newest notifications for one user.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.
        limit : int, default=100
            Maximum number of notifications to return.

        Returns
        -------
        list[Notification]
            Recipient's notifications ordered newest first.
        """
        return self._notification_repository.get_for_user(user_id, limit)

    def get_notifications_after(
        self,
        user_id: int,
        notification_id: int,
        limit: int = MAX_NOTIFICATIONS_PER_REQUEST,
    ) -> list[Notification]:
        """Return notifications newer than a user's SSE event cursor.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.
        notification_id : int
            Last event ID acknowledged by the client.
        limit : int, default=100
            Maximum number of notifications to return.

        Returns
        -------
        list[Notification]
            Notifications ordered oldest first.
        """
        return self._notification_repository.get_after(user_id, notification_id, limit)

    def get_latest_notification_id(self, user_id: int) -> int:
        """Return the most recent notification ID belonging to one user.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.

        Returns
        -------
        int
            Newest notification ID, or zero when none exists.
        """
        return self._notification_repository.get_latest_id_for_user(user_id)

    def mark_notification_read(
        self, user_id: int, notification_id: int
    ) -> Notification:
        """Mark one of a user's notifications as read.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.
        notification_id : int
            Identifier of the notification to mark as read.

        Returns
        -------
        Notification
            Updated notification.

        Raises
        ------
        LookupError
            If the notification does not belong to the user or does not exist.
        """
        return self._notification_repository.mark_read(user_id, notification_id)

    def close(self) -> None:
        """Dispose of the database engine owned by this service."""
        self._database.close()
