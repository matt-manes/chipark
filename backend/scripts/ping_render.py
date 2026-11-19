import random
import time
from datetime import datetime, timedelta

import requests

""" 
Send a request to the Render hosted backend periodically to prevent service from going to sleep.
"""


def main() -> None:
    endpoint: str = "https://api-chipark.onrender.com"
    while "forever":
        try:
            response: requests.Response = requests.get(endpoint)
            print(f"{response.status_code=}")
            print(f"{response.json()}")
        except Exception as e:
            print(f"{type(e).__name__}: {e}")
        sleep_time: int = random.randint(60 * 8, 60 * 12)
        print(f"Sleeping until {datetime.now() + timedelta(seconds=sleep_time)}.")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
