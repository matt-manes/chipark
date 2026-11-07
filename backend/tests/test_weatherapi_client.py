from backend.clients.weatherapi_client import WeatherApiClient
from backend.models.conditions import Conditions
from backend.models.park import Park


def test_get_current_conditions_returns_data(sample_park: Park) -> None:
    client: WeatherApiClient = WeatherApiClient()
    conditions: Conditions = client.get_current_conditions(
        sample_park.lat, sample_park.lon
    )
    assert conditions
