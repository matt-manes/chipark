from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.engine import Engine

from backend.tools.config import Config

from .database import Database


class PostgresqlDatabase(Database):
    """Configure a PostgreSQL database using the shared settings.

    Parameters
    ----------
    database_url : str
        SQLAlchemy PostgreSQL URL without username or password.

    Raises
    ------
    ValueError
        If PostgreSQL username or password settings are missing.
    """

    def __init__(
        self,
        database_url: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize the PostgreSQL database.

        Parameters
        ----------
        database_url : str
            SQLAlchemy PostgreSQL URL without username or password.
        username : str | None
            Optional explicit database username, used instead of application
            credentials.
        password : str | None
            Optional explicit database password, used instead of application
            credentials.
        """
        self._database_url: str = database_url
        self._username: str | None = username
        self._password: str | None = password
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
            If either required credential setting is missing.
        """
        config: Config = Config()
        username: str | None = (
            self._username if self._username is not None else config.CHIPARK_PG_USER
        )
        password: str | None = (
            self._password if self._password is not None else config.CHIPARK_PG_PASS
        )
        if username is None or password is None:
            raise ValueError(
                "Set CHIPARK_PG_USER and CHIPARK_PG_PASS to use PostgreSQL."
            )

        database_url: URL = make_url(self._database_url)
        if not database_url.drivername.startswith("postgresql"):
            raise ValueError("CHIPARK_PG_URL must use a PostgreSQL scheme.")
        authenticated_url: URL = database_url.set(
            username=username,
            password=password,
        )
        return create_engine(authenticated_url)
