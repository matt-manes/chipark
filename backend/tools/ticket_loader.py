import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.models.ticket import Ticket, TicketStatus

DEFAULT_PATH: Path = Path(__file__).parent.parent / "data" / "synthetic-tickets.json"


def to_ticket(data: dict[str, Any]) -> Ticket:
    return Ticket(
        data["park_name"],
        TicketStatus.OPEN if data["status"] == "OPEN" else TicketStatus.CLOSED,
        datetime.fromisoformat(data["file_date"]),
        data["estimated_hours"],
        data["issue"],
    )


def load_from_json(path: Path = DEFAULT_PATH) -> list[Ticket]:
    data: list[dict[str, Any]] = json.loads(path.read_text())
    return [to_ticket(datum) for datum in data]
