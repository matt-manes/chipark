from ..tools.config import Config
from .database import Database
from .postgresql_database import PostgresqlDatabase
from .sqlite_database import SqliteDatabase


class DatabaseFactoryError(ValueError):
    """Error raised when a requested database implementation is unavailable."""


class DatabaseFactory:
    """Create database implementations by configured engine name."""

    @staticmethod
    def get_database(database_type: str) -> Database:
        """
        Create a database implementation for the requested engine.

        Parameters
        ----------
        database_type : str
            Configured database engine name.

        Returns
        -------
        Database
            Database implementation for the requested engine.

        Raises
        ------
        DatabaseFactoryError
            If no database implementation is registered for ``database_type``.
        """
        if database_type.casefold() == "sqlite":
            return SqliteDatabase()
        if database_type.casefold() in {"postgresql", "postgres"}:
            return PostgresqlDatabase(Config().CHIPARK_PG_URL)
        raise DatabaseFactoryError(f"Unsupported database type '{database_type}'.")
