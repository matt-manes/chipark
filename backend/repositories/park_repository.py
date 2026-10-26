from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.park import Park
from .entities import ParkRecord


class ParkRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory: sessionmaker[Session] = session_factory

    def add(self, park: Park) -> Park:
        with self._session_factory.begin() as session:
            record = ParkRecord(
                park_id=park.park_id if park.park_id >= 0 else None,
                park_no=park.park_no,
                name=park.name,
                street=park.street,
                zip_code=park.zip_code,
                acres=park.acres,
                ward=park.ward,
                park_class=park.park_class,
                label=park.label,
                lat=park.lat,
                lon=park.lon,
            )
            session.add(record)
            session.flush()
            return self._to_model(record)

    def get_all(self) -> list[Park]:
        with self._session_factory() as session:
            records: Sequence[ParkRecord] = session.scalars(
                select(ParkRecord).order_by(ParkRecord.park_id)
            ).all()
            return [self._to_model(record) for record in records]

    @staticmethod
    def _to_model(record: ParkRecord) -> Park:
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
