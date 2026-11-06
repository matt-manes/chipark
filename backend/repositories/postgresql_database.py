import os

from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.engine import Engine

from .database import Database


class PostgresqlDatabase(Database):
    """Configure a PostgreSQL database using URL and environment credentials.

    Parameters
    ----------
    database_url : str
        SQLAlchemy PostgreSQL URL without username or password.

    Raises
    ------
    ValueError
        If PostgreSQL username or password environment variables are missing.
    """

    _USERNAME_ENVIRONMENT_VARIABLE: str = "CHIPARK_PG_USER"
    _PASSWORD_ENVIRONMENT_VARIABLE: str = "CHIPARK_PG_PASS"

    def __init__(self, database_url: str) -> None:
        """Initialize the PostgreSQL database.

        Parameters
        ----------
        database_url : str
            SQLAlchemy PostgreSQL URL without username or password.
        """
        self._database_url: str = database_url
        super().__init__()

    def _create_engine(self) -> Engine:
        """Create an engine with credentials supplied by the environment.

        Returns
        -------
        Engine
            Engine configured for the PostgreSQL database.

        Raises
        ------
        ValueError
            If either required credential environment variable is missing.
        """
        username: str | None = os.environ.get(self._USERNAME_ENVIRONMENT_VARIABLE)
        password: str | None = os.environ.get(self._PASSWORD_ENVIRONMENT_VARIABLE)
        if username is None or password is None:
            raise ValueError(
                f"Set {self._USERNAME_ENVIRONMENT_VARIABLE} and "
                f"{self._PASSWORD_ENVIRONMENT_VARIABLE} to use PostgreSQL."
            )

        database_url: URL = make_url(self._database_url)
        if not database_url.drivername.startswith("postgresql"):
            raise ValueError("CHIPARK_PG_URL must use a PostgreSQL scheme.")
        authenticated_url: URL = database_url.set(
            username=username,
            password=password,
        )
        return create_engine(authenticated_url)
