from collections.abc import Sequence

from ..models.park import Park
from ..models.ticket import Ticket
from ..repositories import Database, ParkRepository, TicketRepository


class DataService:
    def __init__(self, database: Database) -> None:
        self._database: Database = database
        self._park_repository: ParkRepository = ParkRepository(
            self._database.session_factory
        )
        self._ticket_repository: TicketRepository = TicketRepository(
            self._database.session_factory
        )

    def add_park(self, park: Park) -> Park:
        return self._park_repository.add(park)

    def add_parks(self, parks: Sequence[Park]) -> None:
        for park in parks:
            self.add_park(park)

    def get_parks(self) -> list[Park]:
        return self._park_repository.get_all()

    def get_ticket(self, ticket_id: int) -> Ticket:
        return self._ticket_repository.get(ticket_id)

    def get_tickets(self) -> list[Ticket]:
        return self._ticket_repository.get_all()

    def add_ticket(self, ticket: Ticket) -> Ticket:
        return self._ticket_repository.add(ticket)

    def close_ticket(self, ticket_id: int) -> Ticket:
        return self._ticket_repository.close(ticket_id)
