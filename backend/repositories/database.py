from pathlib import Path

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .entities import Base

DEFAULT_DATABASE_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "chipark.sqlite3"
)


class SqliteDatabase:
    def __init__(self, database_path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        self.engine: Engine = self._create_engine(database_path)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _create_engine(database_path: Path | str) -> Engine:
        if str(database_path) == ":memory:":
            url: URL = URL.create("sqlite", database=":memory:")
        else:
            resolved_path = Path(database_path)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            url = URL.create("sqlite", database=str(resolved_path.resolve()))
        return create_engine(url)

    def close(self) -> None:
        self.engine.dispose()
