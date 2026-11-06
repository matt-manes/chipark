import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus
from backend.repositories.database import Database
from backend.repositories.park_repository import ParkRepository
from backend.repositories.postgresql_database import PostgresqlDatabase
from backend.repositories.sqlite_database import SqliteDatabase
from backend.repositories.ticket_repository import TicketRepository


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    postgresql_url: str | None = os.environ.get("CHIPARK_TEST_PG_URL")
    if postgresql_url is not None:
        yield from _postgresql_test_database(postgresql_url)
        return

    yield from _sqlite_test_database(tmp_path)


@pytest.fixture
def sqlite_database(tmp_path: Path) -> Iterator[SqliteDatabase]:
    yield from _sqlite_test_database(tmp_path)


def _sqlite_test_database(tmp_path: Path) -> Iterator[SqliteDatabase]:
    """Create a temporary SQLite database for a test.

    Parameters
    ----------
    tmp_path : Path
        Pytest's temporary directory for the current test.

    Yields
    ------
    SqliteDatabase
        Database stored in the test's temporary directory.
    """
    database_path: Path = tmp_path / "chipark.sqlite3"
    database: SqliteDatabase = SqliteDatabase(database_path)
    try:
        yield database
    finally:
        database.close()


def _postgresql_test_database(postgresql_url: str) -> Iterator[Database]:
    """Create an isolated PostgreSQL schema for one test.

    Parameters
    ----------
    postgresql_url : str
        PostgreSQL test-database URL without credentials.

    Yields
    ------
    Database
        Database bound to a temporary schema that is dropped after the test.

    Raises
    ------
    RuntimeError
        If the URL does not target a database whose name contains ``test`` or
        required PostgreSQL credentials are absent.
    ValueError
        If the supplied URL does not use a PostgreSQL scheme.
    """
    base_url: URL = make_url(postgresql_url)
    if not base_url.drivername.startswith("postgresql"):
        raise ValueError("CHIPARK_TEST_PG_URL must use a PostgreSQL scheme.")
    if base_url.database is None or "test" not in base_url.database.casefold():
        raise RuntimeError(
            "CHIPARK_TEST_PG_URL must target a dedicated database with 'test' "
            "in its name."
        )

    username: str | None = os.environ.get("CHIPARK_PG_USER")
    password: str | None = os.environ.get("CHIPARK_PG_PASS")
    if username is None or password is None:
        raise RuntimeError(
            "Set CHIPARK_PG_USER and CHIPARK_PG_PASS to use PostgreSQL tests."
        )

    authenticated_url: URL = base_url.set(username=username, password=password)
    admin_engine = create_engine(authenticated_url)
    schema_name: str = f"chipark_test_{uuid4().hex}"
    database: PostgresqlDatabase | None = None
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

        query: dict[str, str | tuple[str, ...]] = dict(base_url.query)
        raw_options: str | tuple[str, ...] | None = base_url.query.get("options")
        existing_options: str = (
            " ".join(raw_options)
            if isinstance(raw_options, tuple)
            else raw_options or ""
        )
        schema_options: str = f"-c search_path={schema_name}"
        query["options"] = (
            f"{existing_options} {schema_options}".strip()
            if existing_options
            else schema_options
        )
        isolated_url: URL = base_url.set(query=query)
        database = PostgresqlDatabase(isolated_url.render_as_string(hide_password=True))
        yield database
    finally:
        try:
            if database is not None:
                database.close()
        finally:
            try:
                with admin_engine.begin() as connection:
                    connection.execute(
                        text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                    )
            finally:
                admin_engine.dispose()


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
