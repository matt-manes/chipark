from pathlib import Path

from sqlalchemy import inspect

from backend.models.park import Park
from backend.repositories.park_repository import ParkRepository
from backend.repositories.sqlite_database import SqliteDatabase


def test_creates_schema(database: SqliteDatabase) -> None:
    table_names: list[str] = inspect(database.engine).get_table_names()
    assert table_names == ["parks", "tickets"]


def test_creates_database_parent_directory(tmp_path: Path) -> None:
    database_path: Path = tmp_path / "nested" / "data" / "chipark.sqlite3"
    database: SqliteDatabase = SqliteDatabase(database_path)
    try:
        assert database_path.parent.is_dir()
        assert Path(database.engine.url.database or "").exists()
    finally:
        database.close()


def test_file_database_preserves_data_when_reopened(
    tmp_path: Path, sample_park: Park
) -> None:
    database_path: Path = tmp_path / "chipark.sqlite3"
    first_database: SqliteDatabase = SqliteDatabase(database_path)
    saved_park: Park = ParkRepository(first_database.session_factory).add(sample_park)
    first_database.close()

    second_database: SqliteDatabase = SqliteDatabase(database_path)
    try:
        parks: list[Park] = ParkRepository(second_database.session_factory).get_all()
        assert parks == [saved_park]
    finally:
        second_database.close()
