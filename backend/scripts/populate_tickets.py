from backend.repositories import Database
from backend.tools.ticket_loader import load_from_json

from ..models.ticket import Ticket
from ..repositories.sqlite_database import SqliteDatabase
from ..services.data_service import DataService


class TicketDatabasePopulator:
    def __init__(self) -> None:
        self._database: Database = SqliteDatabase()
        self._data_service: DataService = DataService(self._database)
        self._starting_count: int = len(self._data_service.get_tickets())

    def populate(self) -> int:
        try:
            tickets: list[Ticket] = load_from_json()
            for ticket in tickets:
                self._data_service.add_ticket(ticket)
            return len(self._data_service.get_tickets()) - self._starting_count
        finally:
            self._database.close()


def main() -> None:
    inserted_count: int = TicketDatabasePopulator().populate()
    print(f"Inserted {inserted_count} tickets")


if __name__ == "__main__":
    main()
