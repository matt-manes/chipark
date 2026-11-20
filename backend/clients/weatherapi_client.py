from datetime import UTC, datetime
from typing import Any

import requests

from backend.models.conditions import Conditions
from backend.tools.config import Config


class WeatherApiClient:
    """Fetch current weather conditions from WeatherAPI.

    The API key is loaded through the shared application configuration.
    """

    def __init__(self) -> None:
        """Initialize the client with its configured API key.

        Raises
        ------
        ValueError
            If the WeatherAPI key is not configured.
        """
        self._api_key: str = self._load_api_key()

    @property
    def _base_url(self) -> str:
        """Return the current-conditions endpoint with the API key."""
        return f"https://api.weatherapi.com/v1/current.json?key={self._api_key}"

    def _load_api_key(self) -> str:
        """Read the WeatherAPI key from the process environment.

        Returns
        -------
        str
            Configured API key.

        Raises
        ------
        ValueError
            If the environment variable is missing or empty.
        """
        _api_key: str | None = Config().CHIPARK_WEATHERAPI_KEY
        if not _api_key:
            raise ValueError("Set CHIPARK_WEATHERAPI_KEY to use WeatherAPI.")
        return _api_key

    def get_current_conditions(self, lat: float, lon: float) -> Conditions:
        """Fetch current weather conditions for the given coordinates.

        Parameters
        ----------
        lat : float
            Latitude of the location.
        lon : float
            Longitude of the location.

        Returns
        -------
        Conditions
            Current weather conditions returned by WeatherAPI.

        Raises
        ------
        requests.HTTPError
            If WeatherAPI returns an unsuccessful HTTP status.
        requests.RequestException
            If the request cannot be completed.
        KeyError
            If the response is missing an expected field.
        """
        url: str = f"{self._base_url}&q={lat}%2c{lon}&aqi=no"
        response: requests.Response = requests.get(url)
        response.raise_for_status()
        data: dict[str, Any] = response.json()["current"]
        return Conditions(
            datetime.fromtimestamp(data["last_updated_epoch"], tz=UTC),
            data["temp_f"],
            data["condition"]["text"],
            data["wind_mph"],
            data["wind_dir"],
            data["precip_in"],
            data["humidity"],
            data["cloud"],
            data["feelslike_f"],
            data["heatindex_f"],
            data["uv"],
            data["chance_of_rain"],
            data["chance_of_snow"],
        )
