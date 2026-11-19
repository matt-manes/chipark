from rich.progress import track

from backend.repositories import Database

from ..models.park import Park
from ..repositories.database_factory import DatabaseFactory
from ..services.data_service import DataService
from ..tools.config import Config
from ..tools.park_loader import load_from_geojson


class ParkDatabasePopulator:
    """Load park features and insert parks that are not already stored."""

    def __init__(self) -> None:
        """Create the database-backed data service used for population."""
        self._database: Database = DatabaseFactory.get_database(
            Config().CHIPARK_DATABASE
        )
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
            for park in track(parks, "Populating parks..."):
                if park.park_no not in self._park_nos:
                    self._data_service.add_park(park)
            return len(self._data_service.get_parks()) - self._starting_count
        finally:
            self._database.close()


def main() -> None:
    inserted_count: int = ParkDatabasePopulator().populate()
    print(f"Inserted {inserted_count} parks")


if __name__ == "__main__":
    main()
