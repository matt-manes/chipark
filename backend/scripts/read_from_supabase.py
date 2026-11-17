import random
import time
from datetime import datetime

from ..models.park import Park
from ..repositories.database import Database
from ..repositories.database_factory import DatabaseFactory
from ..services.data_service import DataService
from ..tools.config import Config

""" 
Fetch random amounts of data every few hours so project doesn't get paused for inactivity.
"""


def main() -> None:
    """ """
    if "supabase" not in Config().CHIPARK_PG_URL:
        print("Environment not currently configured to use supabase remote db.")
        return
    database: Database = DatabaseFactory.get_database("postgres")
    data_service: DataService = DataService(database)
    while "forever":
        print(f"Fetching data at {datetime.now()}.")
        try:
            print("Fetching parks")
            parks: list[Park] = data_service.get_parks()
            for _ in range(random.randint(1, 10)):
                park: Park = random.choice(parks)
                print(f"Fetching tickets for {park.name}.")
                park_id: int = park.park_id
                print(
                    *[
                        f"{ticket.status}: {ticket.issue}"
                        for ticket in data_service.get_tickets_for_park(park_id)
                    ],
                    sep="\n",
                )
        except Exception as e:
            print(e)
        sleep_time: int = random.randint(3600, 3600 * 6)
        print(f"Sleeping for {float(sleep_time)/3600:.2f} hours.")
        time.sleep(random.randint(3600, 3600 * 6))


if __name__ == "__main__":
    main()
