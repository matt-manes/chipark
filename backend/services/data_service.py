from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Self

from starlette.requests import Request

from ..clients.weatherapi_client import WeatherApiClient
from ..models.conditions import Conditions
from ..models.notification import MAX_NOTIFICATIONS_PER_REQUEST, Notification
from ..models.park import Park
from ..models.ticket import Ticket, TicketUpdate
from ..repositories import (
    ConditionsRepository,
    Database,
    NotificationRepository,
    ParkRepository,
    TicketRepository,
)
from ..tools.config import Config


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
        self._conditions_repository: ConditionsRepository = ConditionsRepository(
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

    def get_conditions(self, park_id: int) -> Conditions | None:
        """Return current weather conditions, refreshing the cache when stale.

        Parameters
        ----------
        park_id : int
            Identifier of the park whose weather is requested.

        Returns
        -------
        Conditions or None
            Cached or freshly fetched conditions. Returns ``None`` if the
            weather client has no conditions to provide.

        Raises
        ------
        LookupError
            If the park does not exist.
        """
        cached_conditions: Conditions | None = self._conditions_repository.get_for_park(
            park_id
        )
        if self._conditions_cache_is_fresh(cached_conditions):
            return cached_conditions

        park: Park = self.get_park(park_id)
        current_conditions: Conditions
        try:
            current_conditions = WeatherApiClient().get_current_conditions(
                park.lat, park.lon
            )
        except Exception as e:
            # TODO replace with logging
            print(e)
            return None
        if cached_conditions is None:
            return self._conditions_repository.add(park_id, current_conditions)
        return self._conditions_repository.update(park_id, current_conditions)

    def get_park_with_conditions(self, park_id: int) -> Park:
        """Return a park with its current weather conditions populated.

        Parameters
        ----------
        park_id : int
            Identifier of the park to retrieve.

        Returns
        -------
        Park
            Park with cached or freshly fetched conditions.

        Raises
        ------
        LookupError
            If the park does not exist.
        """
        park: Park = self.get_park(park_id)
        park.conditions = self.get_conditions(park_id)
        return park

    @staticmethod
    def _conditions_cache_is_fresh(conditions: Conditions | None) -> bool:
        """Determine whether cached conditions fall within the configured TTL.

        Parameters
        ----------
        conditions : Conditions or None
            Cached conditions, if present.

        Returns
        -------
        bool
            Whether the cache entry is fresh.
        """
        if conditions is None:
            return False
        expires_at: datetime = conditions.last_updated + timedelta(
            seconds=Config().CHIPARK_CONDITIONS_TTL
        )
        return datetime.now() <= expires_at

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

    def get_tickets_for_user(self, user_id: int) -> list[Ticket]:
        """Retrieve tickets submitted by one user.

        Parameters
        ----------
        user_id : int
            Submitter account identifier.

        Returns
        -------
        list[Ticket]
            Tickets submitted by the requested account.
        """
        return self._ticket_repository.get_for_user(user_id)

    def get_open_tickets_for_park(self, park_id: int) -> list[Ticket]:
        """Retrieve open tickets associated with a park identifier.

        Parameters
        ----------
        park_id : int
            Database identifier of the park.

        Returns
        -------
        list[Ticket]
            Open tickets associated with the requested park.

        Raises
        ------
        LookupError
            If the park does not exist.
        """
        park: Park = self.get_park(park_id)
        return self._ticket_repository.get_open_for_park(park.name)

    def get_tickets_for_park(self, park_id: int) -> list[Ticket]:
        """
        Retrieve tickets associated with a park identifier.

        Parameters
        ----------
        park_id : int
            Database id of the park

        Returns
        -------
        list[Ticket]
            Open tickets associated with the requested park.

        Raises
        ------
        LookupError
            If the park does not exist.
        """
        park: Park = self.get_park(park_id)
        return self._ticket_repository.get_tickets_for_park(park.name)

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

    def reopen_ticket(self, ticket_id: int) -> Ticket:
        """Reopen an existing ticket.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to reopen.

        Returns
        -------
        Ticket
            Updated ticket with open status.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        return self._ticket_repository.reopen(ticket_id)

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
