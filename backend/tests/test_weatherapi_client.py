from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from backend.clients import weatherapi_client
from backend.clients.weatherapi_client import WeatherApiClient
from backend.models.conditions import Conditions
from backend.models.park import Park


def test_get_current_conditions_returns_data(sample_park: Park) -> None:
    client: WeatherApiClient = WeatherApiClient()
    conditions: Conditions = client.get_current_conditions(
        sample_park.lat, sample_park.lon
    )
    assert conditions


def test_weather_timestamp_is_utc(
    monkeypatch: pytest.MonkeyPatch, sample_park: Park
) -> None:
    response: Mock = Mock()
    response.json.return_value = {
        "current": {
            "last_updated_epoch": 0,
            "temp_f": 72,
            "condition": {"text": "Sunny"},
            "wind_mph": 5,
            "wind_dir": "N",
            "precip_in": 0,
            "humidity": 40,
            "cloud": 10,
            "feelslike_f": 72,
            "heatindex_f": 72,
            "uv": 5,
            "chance_of_rain": 0,
            "chance_of_snow": 0,
        }
    }

    def fake_load_api_key(self: WeatherApiClient) -> str:
        return "test"

    def fake_get(url: str) -> Mock:
        return response

    monkeypatch.setattr(WeatherApiClient, "_load_api_key", fake_load_api_key)
    monkeypatch.setattr(weatherapi_client.requests, "get", fake_get)

    conditions: Conditions = WeatherApiClient().get_current_conditions(
        sample_park.lat, sample_park.lon
    )

    assert (
        conditions.last_updated.isoformat()
        == datetime.fromtimestamp(0, UTC).isoformat()
    )
