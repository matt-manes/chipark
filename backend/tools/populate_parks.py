from ..models.park import Park
from ..repositories.sqlite_database import SqliteDatabase
from ..services.data_service import DataService
from .park_loader import load_from_geojson


class ParkDatabasePopulator:
    """Load park features and insert parks that are not already stored."""

    def __init__(self) -> None:
        """Create the SQLite-backed data service used for population."""
        self._database: SqliteDatabase = SqliteDatabase()
        self._data_service: DataService = DataService(self._database)
        self._park_nos: set[str] = {
            park.park_no for park in self._data_service.get_parks()
        }
        self._starting_count: int = len(self._park_nos)

    def populate(self) -> int:
        """
        Insert parks from the default GeoJSON source that are not already stored.

        Returns
        -------
        int
            Number of parks inserted during this run.
        """
        try:
            parks: list[Park] = load_from_geojson()
            self._data_service.add_parks(
                [park for park in parks if park.park_no not in self._park_nos]
            )
            return len(self._data_service.get_parks()) - self._starting_count
        finally:
            self._database.close()


if __name__ == "__main__":
    inserted_count: int = ParkDatabasePopulator().populate()
    print(f"Inserted {inserted_count} parks")
