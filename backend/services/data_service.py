from collections.abc import Sequence
from typing import Self

from backend.tools.config import Config

from ..models.park import Park
from ..models.ticket import Ticket
from ..repositories import Database, DatabaseFactory, ParkRepository, TicketRepository


class DataService:
    """Expose park and ticket operations through their repositories."""

    @classmethod
    def get_default_service(cls) -> Self:
        """
        Returns a DataService instance backed by whatever database is specified in the config.toml/environment.

        Returns
        -------
        DataService
        """
        return cls(DatabaseFactory.get_database(Config().database))

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
