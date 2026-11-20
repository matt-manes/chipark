from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from ..models.conditions import Conditions
from .entities import ConditionsRecord


class ConditionsRepository:
    """Persist cached weather conditions for parks."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Create a repository using the given session factory.

        Parameters
        ----------
        session_factory : sessionmaker[Session]
            Factory bound to the conditions database.
        """
        self._session_factory: sessionmaker[Session] = session_factory

    def get_for_park(self, park_id: int) -> Conditions | None:
        """Return cached weather conditions for a park.

        Parameters
        ----------
        park_id : int
            Identifier of the park whose conditions are requested.

        Returns
        -------
        Conditions or None
            Cached conditions, or ``None`` if the cache has no entry.
        """
        with self._session_factory() as session:
            record: ConditionsRecord | None = session.get(ConditionsRecord, park_id)
            return None if record is None else self._to_model(record)

    def add(self, park_id: int, conditions: Conditions) -> Conditions:
        """Insert cached conditions for a park.

        Parameters
        ----------
        park_id : int
            Identifier of the park.
        conditions : Conditions
            Weather conditions to persist.

        Returns
        -------
        Conditions
            Persisted conditions.
        """
        with self._session_factory.begin() as session:
            record: ConditionsRecord = ConditionsRecord(
                park_id=park_id,
                **self._conditions_values(conditions),
            )
            session.add(record)
            session.flush()
            return self._to_model(record)

    def update(self, park_id: int, conditions: Conditions) -> Conditions:
        """Replace cached conditions for a park.

        Parameters
        ----------
        park_id : int
            Identifier of the park.
        conditions : Conditions
            Refreshed weather conditions.

        Returns
        -------
        Conditions
            Updated conditions.

        Raises
        ------
        LookupError
            If no cached conditions exist for the park.
        """
        with self._session_factory.begin() as session:
            record: ConditionsRecord | None = session.get(ConditionsRecord, park_id)
            if record is None:
                raise LookupError(f"Conditions for park {park_id} were not found")
            for field_name, value in self._conditions_values(conditions).items():
                setattr(record, field_name, value)
            session.flush()
            return self._to_model(record)

    @staticmethod
    def _conditions_values(conditions: Conditions) -> dict[str, object]:
        """Create the database field mapping from a conditions model.

        Parameters
        ----------
        conditions : Conditions
            Weather conditions to map.

        Returns
        -------
        dict[str, object]
            ORM-compatible conditions fields.
        """
        return {
            "last_updated": ConditionsRepository._to_database_time(
                conditions.last_updated
            ),
            "temp_f": conditions.temp_f,
            "condition": conditions.condition,
            "wind_mph": conditions.wind_mph,
            "wind_dir": conditions.wind_dir,
            "precip_in": conditions.precip_in,
            "humidity": conditions.humidity,
            "cloud": conditions.cloud,
            "feels_like_f": conditions.feels_like_f,
            "heat_index_f": conditions.heat_index_f,
            "uv": conditions.uv,
            "chance_of_rain": conditions.chance_of_rain,
            "chance_of_snow": conditions.chance_of_snow,
        }

    @staticmethod
    def _to_database_time(value: datetime) -> datetime:
        """Convert an aware timestamp to the database's naive UTC format.

        Parameters
        ----------
        value : datetime
            Timezone-aware weather observation time.

        Returns
        -------
        datetime
            UTC timestamp without timezone information for database storage.

        Raises
        ------
        ValueError
            If the observation time has no timezone.
        """
        if value.utcoffset() is None:
            raise ValueError("Weather observation time must include a timezone.")
        return value.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def _to_model(record: ConditionsRecord) -> Conditions:
        """Convert a conditions record to its model.

        Parameters
        ----------
        record : ConditionsRecord
            Cached conditions record.

        Returns
        -------
        Conditions
            Conditions represented by the record.
        """
        return Conditions(
            last_updated=record.last_updated.replace(tzinfo=UTC),
            temp_f=record.temp_f,
            condition=record.condition,
            wind_mph=record.wind_mph,
            wind_dir=record.wind_dir,
            precip_in=record.precip_in,
            humidity=record.humidity,
            cloud=record.cloud,
            feels_like_f=record.feels_like_f,
            heat_index_f=record.heat_index_f,
            uv=record.uv,
            chance_of_rain=record.chance_of_rain,
            chance_of_snow=record.chance_of_snow,
        )
