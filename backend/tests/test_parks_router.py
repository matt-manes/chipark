from fastapi.testclient import TestClient
from httpx2 import Response

from backend.models.conditions import Conditions
from backend.models.park import Park
from backend.repositories.conditions_repository import ConditionsRepository
from backend.services.data_service import DataService


def test_get_parks_returns_all_parks(api_client: TestClient, sample_park: Park) -> None:
    response: Response = api_client.get("/parks")

    assert response.status_code == 200
    assert response.json()[0]["name"] == sample_park.name


def test_get_park_returns_park_by_id(
    api_client: TestClient, data_service: DataService, sample_park: Park
) -> None:
    saved_park: Park = data_service.get_parks()[0]

    response: Response = api_client.get(f"/parks/{saved_park.park_id}")

    assert response.status_code == 200
    assert response.json()["name"] == sample_park.name


def test_get_park_returns_404_for_missing_park(api_client: TestClient) -> None:
    response: Response = api_client.get("/parks/999")

    assert response.status_code == 404


def test_get_park_conditions_returns_conditions(api_client: TestClient) -> None:
    response: Response = api_client.get("/parks/1/conditions")
    assert response.status_code == 200
    assert response.json()


def test_get_park_conditions_serializes_timezone(
    api_client: TestClient,
    conditions_repository: ConditionsRepository,
    sample_conditions: Conditions,
) -> None:
    conditions_repository.add(1, sample_conditions)

    response: Response = api_client.get("/parks/1/conditions")

    assert response.json()["last_updated"].endswith(("Z", "+00:00"))


def test_get_park_conditions_returns_404_for_missing_park(
    api_client: TestClient,
) -> None:
    response: Response = api_client.get("/parks/999/conditions")
    assert response.status_code == 404
