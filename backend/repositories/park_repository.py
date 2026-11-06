from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.park import Park
from ..tools.accent_normalizer import AccentNormalizer
from .entities import ParkRecord


class ParkRepository:
    """Persist and retrieve parks using a SQLAlchemy session factory."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """
        Create a repository using the given session factory.

        Parameters
        ----------
        session_factory : sessionmaker[Session]
            Factory bound to the database where park records are stored.
        """
        self._session_factory: sessionmaker[Session] = session_factory

    def add(self, park: Park) -> Park:
        """
        Persist a park and return it with its database identifier.

        Parameters
        ----------
        park : Park
            Park to add.

        Returns
        -------
        Park
            Persisted park model.
        """
        with self._session_factory.begin() as session:
            record = ParkRecord(
                park_id=park.park_id if park.park_id >= 0 else None,
                park_no=park.park_no,
                name=AccentNormalizer.remove_accents(park.name),
                street=(
                    None
                    if park.street is None
                    else AccentNormalizer.remove_accents(park.street)
                ),
                zip_code=park.zip_code,
                acres=park.acres,
                ward=park.ward,
                park_class=park.park_class,
                label=AccentNormalizer.remove_accents(park.label),
                lat=park.lat,
                lon=park.lon,
            )
            session.add(record)
            session.flush()
            return self._to_model(record)

    def get_all(self) -> list[Park]:
        """
        Retrieve all parks ordered by database identifier.

        Returns
        -------
        list[Park]
            Persisted parks in identifier order.
        """
        with self._session_factory() as session:
            records: Sequence[ParkRecord] = session.scalars(
                select(ParkRecord).order_by(ParkRecord.park_id)
            ).all()
            return [self._to_model(record) for record in records]

    def park_exists(self, park_name: str) -> bool:
        """
        Check whether a park with the given name exists.

        Parameters
        ----------
        park_name : str
            Name of the park to find.

        Returns
        -------
        bool
            Whether a matching park exists.
        """
        with self._session_factory() as session:
            park_id: int | None = session.scalar(
                select(ParkRecord.park_id).where(ParkRecord.name == park_name).limit(1)
            )
            return park_id is not None

    def get(self, park_id: int) -> Park:
        """
        Retrieve a park by its database identifier.

        Parameters
        ----------
        park_id : int
            Identifier of the park to retrieve.

        Returns
        -------
        Park
            Matching persisted park.

        Raises
        ------
        LookupError
            If no park has the requested identifier.
        """
        with self._session_factory() as session:
            record: ParkRecord | None = session.get(ParkRecord, park_id)
            if record is None:
                raise LookupError(f"Park {park_id} was not found")
            return self._to_model(record)

    @staticmethod
    def _to_model(record: ParkRecord) -> Park:
        """
        Convert a database record to a park model.

        Parameters
        ----------
        record : ParkRecord
            Database record to convert.

        Returns
        -------
        Park
            Park model represented by the record.
        """
        return Park(
            park_no=record.park_no,
            name=record.name,
            street=record.street,
            zip_code=record.zip_code,
            acres=record.acres,
            ward=record.ward,
            park_class=record.park_class,
            label=record.label,
            lat=record.lat,
            lon=record.lon,
            park_id=record.park_id,
        )
