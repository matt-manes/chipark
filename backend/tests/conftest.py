from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.repositories.database import Database
from backend.repositories.park_repository import ParkRepository
from backend.repositories.sqlite_database import SqliteDatabase
from backend.repositories.ticket_repository import TicketRepository


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    database_path: Path = tmp_path / "chipark.sqlite3"
    database: Database = SqliteDatabase(database_path)
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def park_repository(database: Database) -> ParkRepository:
    return ParkRepository(database.session_factory)


@pytest.fixture
def ticket_repository(database: Database) -> TicketRepository:
    return TicketRepository(database.session_factory)


@pytest.fixture
def sample_park() -> Park:
    return Park(
        park_no="P001",
        name="Sample Park",
        street="123 Main Street",
        zip_code="60601",
        acres="10",
        ward="1",
        park_class="NEIGHBORHOOD PARK",
        label="Sample Park",
        lat=41.88,
        lon=-87.63,
    )


@pytest.fixture
def sample_park2() -> Park:
    return Park(
        park_no="P002",
        name="Sample Park 2",
        street="321 Main Street",
        zip_code="60607",
        acres="3",
        ward="6",
        park_class="NEIGHBORHOOD PARK",
        label="Sample Park 2",
        lat=42.88,
        lon=-87.43,
    )


@pytest.fixture
def sample_ticket() -> Ticket:
    return Ticket(
        park_name="Sample Park",
        status=TicketStatus.OPEN,
        file_date=datetime(2026, 1, 15, 9, 30),
        estimated_hours=2.5,
        issue="Broken bench",
    )
