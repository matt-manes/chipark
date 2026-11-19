import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from backend.models.ticket import Ticket, TicketStatus
from backend.services.data_service import DataService
from backend.tools.ticket_loader import load_from_json, to_ticket


def test_to_ticket_converts_open_ticket() -> None:
    data: dict[str, Any] = {
        "park_name": "Sample Park",
        "status": "OPEN",
        "file_date": "2026-01-15T09:30:00",
        "estimated_hours": 2.5,
        "issue": "Broken bench",
    }
    data_service: Mock = Mock(spec=DataService)
    data_service.get_random_user_id.return_value = 17

    ticket: Ticket = to_ticket(data, data_service)

    assert ticket == Ticket(
        park_name="Sample Park",
        status=TicketStatus.OPEN,
        file_date=datetime(2026, 1, 15, 9, 30),
        estimated_hours=2.5,
        issue="Broken bench",
        user_id=17,
    )


def test_to_ticket_converts_closed_ticket_with_unknown_estimate() -> None:
    data: dict[str, Any] = {
        "park_name": "Sample Park",
        "status": "CLOSED",
        "file_date": "2026-02-01T14:05:00",
        "estimated_hours": None,
        "issue": "Repair pathway",
    }
    data_service: Mock = Mock(spec=DataService)

    ticket: Ticket = to_ticket(data, data_service)

    assert ticket.status is TicketStatus.CLOSED
    assert ticket.file_date == datetime(2026, 2, 1, 14, 5)
    assert ticket.estimated_hours is None


def test_load_from_json_reads_ticket_records(tmp_path: Path) -> None:
    ticket_data: dict[str, Any] = {
        "park_name": "Sample Park",
        "status": "OPEN",
        "file_date": "2026-01-15T09:30:00",
        "estimated_hours": 2.5,
        "issue": "Broken bench",
    }
    json_path: Path = tmp_path / "tickets.json"
    json_path.write_text(json.dumps([ticket_data]))

    data_service: Mock = Mock(spec=DataService)
    data_service.get_random_user_id.return_value = 23

    tickets: list[Ticket] = load_from_json(data_service, json_path)

    assert len(tickets) == 1
    assert tickets[0].park_name == "Sample Park"
    assert tickets[0].user_id == 23
