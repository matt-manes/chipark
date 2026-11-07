import os
from datetime import datetime
from typing import Any

import requests

from backend.models.conditions import Conditions


class WeatherApiClient:
    _WEATHERAPI_KEY_VARIABLE: str = "CHIPARK_WEATHERAPI_KEY"

    def __init__(self) -> None:
        self._api_key: str = self._load_api_key()

    @property
    def _base_url(self) -> str:
        return f"https://api.weatherapi.com/v1/current.json?key={self._api_key}"

    def _load_api_key(self) -> str:
        _api_key: str | None = os.environ.get(self._WEATHERAPI_KEY_VARIABLE)
        if not _api_key:
            raise ValueError("No weatherapi key set in environment.")
        return _api_key

    def get_current_conditions(self, lat: float, lon: float) -> Conditions:
        url: str = f"{self._base_url}&q={lat}%2c{lon}&aqi=no"
        response: requests.Response = requests.get(url)
        response.raise_for_status()
        data: dict[str, Any] = response.json()["current"]
        return Conditions(
            datetime.fromtimestamp(data["last_updated_epoch"]),
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
