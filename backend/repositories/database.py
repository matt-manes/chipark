from abc import ABC, abstractmethod

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .entities import Base


class Database(ABC):
    """
    Provide the shared SQLAlchemy setup for a database implementation.

    Attributes
    ----------
    engine : Engine
        SQLAlchemy engine created by the concrete implementation.
    session_factory : sessionmaker[Session]
        Factory for sessions bound to the engine.
    """

    def __init__(self) -> None:
        """Create the engine, session factory, and mapped database tables."""
        self.engine: Engine = self._create_engine()
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)

    @abstractmethod
    def _create_engine(self) -> Engine:
        """
        Create the SQLAlchemy engine for the concrete database implementation.

        Returns
        -------
        Engine
            Engine configured for the implementation's database.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Dispose of the engine's connection pool."""
        self.engine.dispose()
