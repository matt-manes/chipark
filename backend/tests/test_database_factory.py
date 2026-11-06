import pytest

from backend.repositories.database import Database
from backend.repositories.database_factory import DatabaseFactory, DatabaseFactoryError
from backend.repositories.sqlite_database import SqliteDatabase


@pytest.mark.parametrize("database_type", ["sqlite", "SQLite", "SQLITE"])
def test_get_database_returns_sqlite_for_supported_name(
    database_type: str,
    sqlite_database: SqliteDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.repositories.database_factory.SqliteDatabase",
        lambda: sqlite_database,
    )

    result: Database = DatabaseFactory.get_database(database_type)

    assert result is sqlite_database
    assert isinstance(result, SqliteDatabase)


def test_get_database_raises_for_unsupported_name() -> None:
    with pytest.raises(DatabaseFactoryError, match="Unsupported database type"):
        DatabaseFactory.get_database("yeehaw")


def test_get_database_returns_postgresql_for_supported_name(
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.repositories.database_factory.Config",
        lambda: type(
            "Settings",
            (),
            {"CHIPARK_PG_URL": "postgresql+psycopg2://localhost/chipark"},
        )(),
    )
    monkeypatch.setattr(
        "backend.repositories.database_factory.PostgresqlDatabase",
        lambda database_url: database,  # type: ignore
    )

    result: Database = DatabaseFactory.get_database("PostgreSQL")

    assert result is database
