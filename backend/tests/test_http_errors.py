import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from backend.app import ApplicationFactory, rate_limit_coordinator
from backend.tools.http_errors import ApiCORSMiddleware
from backend.tools.rate_limiting import RateLimitDecision


@pytest.fixture
def throttled_client(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    decision: RateLimitDecision = RateLimitDecision(False, 0, 30)

    def acquire_decision(_ip: str, _auth: bool) -> RateLimitDecision:
        return decision

    monkeypatch.setattr(rate_limit_coordinator, "acquire_decision", acquire_decision)
    return api_client


def test_http_error_uses_detail_array(api_client: TestClient) -> None:
    response: Response = api_client.get("/auth/me", headers={"Authorization": ""})

    assert response.status_code == 401
    assert response.json() == {
        "detail": [
            {
                "type": "http_error",
                "loc": [],
                "msg": "Authentication is required.",
                "input": None,
            }
        ]
    }


def test_http_error_preserves_authentication_header(api_client: TestClient) -> None:
    response: Response = api_client.get("/auth/me", headers={"Authorization": ""})

    assert response.headers["www-authenticate"] == "Bearer"


def test_validation_error_preserves_input_details(api_client: TestClient) -> None:
    response: Response = api_client.get("/parks/not-an-id")

    assert response.status_code == 422
    assert response.json()["detail"][0] == {
        "type": "int_parsing",
        "loc": ["path", "park_id"],
        "msg": "Input should be a valid integer, unable to parse string as an integer",
        "input": "not-an-id",
    }


def test_unknown_route_returns_error_envelope(api_client: TestClient) -> None:
    response: Response = api_client.get("/unknown-route")

    assert response.status_code == 404
    assert response.json()["detail"][0]["msg"] == "Not Found"


def test_unsupported_method_preserves_allow_header(api_client: TestClient) -> None:
    response: Response = api_client.post("/parks")

    assert response.status_code == 405
    assert "GET" in response.headers["allow"]


def test_unsupported_method_uses_error_envelope(api_client: TestClient) -> None:
    response: Response = api_client.post("/parks")

    assert response.json()["detail"][0]["msg"] == "Method Not Allowed"


def test_rate_limit_uses_error_envelope(throttled_client: TestClient) -> None:
    response: Response = throttled_client.get("/parks")

    assert response.status_code == 429
    assert response.json()["detail"][0]["msg"] == "Too many requests. Try again later."


def test_rate_limit_preserves_retry_header(throttled_client: TestClient) -> None:
    response: Response = throttled_client.get("/parks")

    assert response.headers["retry-after"] == "30"


def test_rejected_cors_preflight_uses_error_envelope() -> None:
    application: FastAPI = ApplicationFactory.create(docs_enabled=False)
    application.add_middleware(
        ApiCORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    client: TestClient = TestClient(application)
    response: Response = client.options(
        "/parks",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"][0]["msg"] == "Disallowed CORS origin"
    assert "Origin" in response.headers["vary"]


def test_mcp_transport_keeps_its_own_error_format(api_client: TestClient) -> None:
    response: Response = api_client.get("/mcp", headers={"Host": "invalid.example"})

    assert response.status_code == 421
    assert response.text == "Invalid Host header"


def test_unexpected_error_does_not_expose_exception() -> None:
    application: FastAPI = ApplicationFactory.create(docs_enabled=False)

    @application.get("/failure")
    async def fail() -> None:
        raise RuntimeError("private exception details")

    client: TestClient = TestClient(application, raise_server_exceptions=False)
    response: Response = client.get("/failure")

    assert response.status_code == 500
    assert response.json()["detail"][0]["msg"] == "Internal Server Error"
