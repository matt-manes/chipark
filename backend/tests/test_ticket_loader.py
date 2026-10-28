import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.models.ticket import Ticket, TicketStatus
from backend.tools.ticket_loader import load_from_json, to_ticket


def test_to_ticket_converts_open_ticket() -> None:
    data: dict[str, Any] = {
        "park_name": "Sample Park",
        "status": "OPEN",
        "file_date": "2026-01-15T09:30:00",
        "estimated_hours": 2.5,
        "issue": "Broken bench",
    }

    ticket: Ticket = to_ticket(data)

    assert ticket == Ticket(
        park_name="Sample Park",
        status=TicketStatus.OPEN,
        file_date=datetime(2026, 1, 15, 9, 30),
        estimated_hours=2.5,
        issue="Broken bench",
    )


def test_to_ticket_converts_closed_ticket_with_unknown_estimate() -> None:
    data: dict[str, Any] = {
        "park_name": "Sample Park",
        "status": "CLOSED",
        "file_date": "2026-02-01T14:05:00",
        "estimated_hours": None,
        "issue": "Repair pathway",
    }

    ticket: Ticket = to_ticket(data)

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

    tickets: list[Ticket] = load_from_json(json_path)

    assert len(tickets) == 1
    assert tickets[0].park_name == "Sample Park"
