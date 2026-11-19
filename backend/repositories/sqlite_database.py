from pathlib import Path

from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection, DBAPICursor
from sqlalchemy.pool import ConnectionPoolEntry

from .database import Database

DEFAULT_DATABASE_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "chipark.sqlite3"
)


class SqliteDatabase(Database):
    """
    Configure a SQLite database and create its parent directory when needed.

    Parameters
    ----------
    database_path : Path or str, default=DEFAULT_DATABASE_PATH
        SQLite file path, or ``":memory:"`` for an in-memory database.
    """

    def __init__(self, database_path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        """Initialize the SQLite database at ``database_path``.

        Parameters
        ----------
        database_path : Path or str, default=DEFAULT_DATABASE_PATH
            SQLite file path, or ``":memory:"`` for an in-memory database.
        """
        self._database_path: Path | str = database_path
        super().__init__()

    def _create_engine(self) -> Engine:
        """
        Create an engine connected to the configured SQLite database.

        Returns
        -------
        Engine
            Engine connected to the SQLite file or in-memory database.
        """
        if str(self._database_path) == ":memory:":
            url: URL = URL.create("sqlite", database=":memory:")
        else:
            resolved_path: Path = Path(self._database_path)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            url = URL.create("sqlite", database=str(resolved_path.resolve()))
        engine: Engine = create_engine(url)
        event.listen(engine, "connect", self._enable_foreign_keys)
        return engine

    @staticmethod
    def _enable_foreign_keys(
        dbapi_connection: DBAPIConnection,
        _connection_record: ConnectionPoolEntry,
    ) -> None:
        """
        Enable foreign-key enforcement on each SQLite connection.

        Parameters
        ----------
        dbapi_connection : DBAPIConnection
            Newly created SQLite DB-API connection.
        _connection_record : ConnectionPoolEntry
            SQLAlchemy connection pool entry for the connection.
        """
        cursor: DBAPICursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
