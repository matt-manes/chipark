from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from backend.models.park import Park
from backend.services.data_service import DataService


@dataclass(frozen=True)
class OwnedTicket:
    ticket_id: int
    park_id: int
    user_id: int
    token: str
    response_user_id: int | None

    def path(self, template: str) -> str:
        return template.format(ticket_id=self.ticket_id, park_id=self.park_id)


class TicketResponse:
    @staticmethod
    def user_id(response: Response) -> object:
        assert response.status_code == 200
        body: dict[str, object] | list[dict[str, object]] = response.json()
        ticket: dict[str, object] = body[0] if isinstance(body, list) else body
        return ticket["user_id"]


@pytest.fixture
def owned_ticket(
    api_client: TestClient, sample_park: Park, data_service: DataService
) -> OwnedTicket:
    registration: Response = api_client.post(
        "/auth/register",
        json={"email": "ticket-owner@example.com", "password": "a-secure-password"},
    )
    token: str = registration.json()["access_token"]
    response: Response = api_client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={"park_name": sample_park.name, "issue": "Broken bench"},
    )
    assert response.status_code == 201
    return OwnedTicket(
        ticket_id=response.json()["ticket_id"],
        park_id=data_service.get_parks()[0].park_id,
        user_id=registration.json()["user"]["user_id"],
        token=token,
        response_user_id=response.json()["user_id"],
    )


@pytest.mark.parametrize(
    "path", ["/tickets", "/tickets/{ticket_id}", "/tickets/parks/{park_id}/open"]
)
def test_anonymous_ticket_responses_hide_user_id(
    api_client: TestClient, owned_ticket: OwnedTicket, path: str
) -> None:
    del api_client.headers["Authorization"]
    response: Response = api_client.get(owned_ticket.path(path))

    assert TicketResponse.user_id(response) is None


@pytest.mark.parametrize(
    "path", ["/tickets", "/tickets/{ticket_id}", "/tickets/parks/{park_id}/open"]
)
@pytest.mark.parametrize("authorization", ["", "Bearer invalid-token"])
def test_invalid_credentials_do_not_expose_user_id(
    api_client: TestClient, owned_ticket: OwnedTicket, path: str, authorization: str
) -> None:
    response: Response = api_client.get(
        owned_ticket.path(path), headers={"Authorization": authorization}
    )

    assert TicketResponse.user_id(response) is None


@pytest.mark.parametrize(
    "path", ["/tickets", "/tickets/{ticket_id}", "/tickets/parks/{park_id}/open"]
)
def test_regular_user_ticket_responses_hide_user_id(
    api_client: TestClient, owned_ticket: OwnedTicket, path: str
) -> None:
    response: Response = api_client.get(
        owned_ticket.path(path),
        headers={"Authorization": f"Bearer {owned_ticket.token}"},
    )

    assert TicketResponse.user_id(response) is None


@pytest.mark.parametrize(
    "path", ["/tickets", "/tickets/{ticket_id}", "/tickets/parks/{park_id}/open"]
)
def test_admin_ticket_responses_include_user_id(
    api_client: TestClient, owned_ticket: OwnedTicket, path: str
) -> None:
    response: Response = api_client.get(owned_ticket.path(path))

    assert TicketResponse.user_id(response) == owned_ticket.user_id


def test_regular_user_ticket_submission_hides_user_id(
    owned_ticket: OwnedTicket,
) -> None:
    assert owned_ticket.response_user_id is None


def test_regular_user_my_tickets_hides_user_id(
    api_client: TestClient, owned_ticket: OwnedTicket
) -> None:
    response: Response = api_client.get(
        "/tickets/mine", headers={"Authorization": f"Bearer {owned_ticket.token}"}
    )

    assert TicketResponse.user_id(response) is None


@pytest.mark.parametrize(
    "path", ["/tickets", "/tickets/{ticket_id}", "/tickets/parks/{park_id}/open"]
)
def test_ticket_responses_are_not_cacheable(
    api_client: TestClient, owned_ticket: OwnedTicket, path: str
) -> None:
    response: Response = api_client.get(owned_ticket.path(path))

    assert response.headers["cache-control"] == "private, no-store"
