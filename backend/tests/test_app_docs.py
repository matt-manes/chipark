import pytest
from fastapi.testclient import TestClient

from backend.app import ApplicationFactory


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_routes_are_available_when_enabled(path: str) -> None:
    client: TestClient = TestClient(ApplicationFactory.create(True))

    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_routes_are_unavailable_when_disabled(path: str) -> None:
    client: TestClient = TestClient(ApplicationFactory.create(False))

    assert client.get(path).status_code == 404
