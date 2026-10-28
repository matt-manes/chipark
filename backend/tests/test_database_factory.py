import pytest

from backend.repositories.database import Database
from backend.repositories.database_factory import DatabaseFactory, DatabaseFactoryError
from backend.repositories.sqlite_database import SqliteDatabase


@pytest.mark.parametrize("database_type", ["sqlite", "SQLite", "SQLITE"])
def test_get_database_returns_sqlite_for_supported_name(
    database_type: str,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.repositories.database_factory.SqliteDatabase",
        lambda: database,
    )

    result: Database = DatabaseFactory.get_database(database_type)

    assert result is database
    assert isinstance(result, SqliteDatabase)


def test_get_database_raises_for_unsupported_name() -> None:
    with pytest.raises(DatabaseFactoryError, match="Unsupported database type"):
        DatabaseFactory.get_database("yeehaw")
