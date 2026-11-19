import random
import time
from datetime import datetime, timedelta

import psycopg2

from ..models.park import Park
from ..repositories.database import Database
from ..repositories.database_factory import DatabaseFactory
from ..services.data_service import DataService
from ..tools.config import Config

""" 
Fetch random amounts of data every few hours so project doesn't get paused for inactivity.
"""


def main() -> None:
    if "supabase" not in Config().CHIPARK_PG_URL:
        print("Environment not currently configured to use supabase remote db.")
        return
    consecutive_fails: int = 0
    fail_limit: int = 5
    while "forever":
        database: Database | None = None
        try:
            database = DatabaseFactory.get_database("postgres")
            data_service: DataService = DataService(database)
            print(f"Fetching data at {datetime.now()}.")
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
        except psycopg2.OperationalError:
            consecutive_fails += 1
            if consecutive_fails >= fail_limit:
                print("Fail limit exceeded")
            else:
                print("Server closed connection. Retrying...")
                continue
        except Exception as e:
            print(e)
        if database:
            database.close()
        consecutive_fails = 0
        sleep_time: int = random.randint(3600 * 6, 3600 * 12)
        print(f"Sleeping until {datetime.now() + timedelta(seconds=sleep_time)}.")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
