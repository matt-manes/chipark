from abc import ABC, abstractmethod

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .entities import Base


class Database(ABC):
    def __init__(self) -> None:
        self.engine: Engine = self._create_engine()
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)

    @abstractmethod
    def _create_engine(self) -> Engine:
        raise NotImplementedError

    def close(self) -> None:
        self.engine.dispose()
