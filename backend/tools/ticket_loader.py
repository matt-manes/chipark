import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.models.ticket import Ticket, TicketStatus
from backend.services.data_service import DataService

DEFAULT_PATH: Path = Path(__file__).parent.parent / "data" / "synthetic-tickets.json"


def to_ticket(data: dict[str, Any], data_service: DataService) -> Ticket:
    """
    Convert a JSON ticket record into a ticket model.

    Parameters
    ----------
    data : dict[str, Any]
        Ticket fields, with status as ``"OPEN"`` or ``"CLOSED"`` and the
        filing date as an ISO-formatted string.
    data_service : DataService
        Service used to choose a submitting user.

    Returns
    -------
    Ticket
        Ticket model populated from the record.
    """
    return Ticket(
        data["park_name"],
        TicketStatus.OPEN if data["status"] == "OPEN" else TicketStatus.CLOSED,
        datetime.fromisoformat(data["file_date"]),
        data["estimated_hours"],
        data["issue"],
        user_id=data_service.get_random_user_id(),
    )


def load_from_json(
    data_service: DataService, path: Path = DEFAULT_PATH
) -> list[Ticket]:
    """
    Load ticket models from a JSON file.

    Parameters
    ----------
    data_service : DataService
        Service used to choose a submitting user for each ticket.
    path : Path, default=DEFAULT_PATH
        Path to the JSON file containing a list of ticket records.

    Returns
    -------
    list[Ticket]
        Ticket models converted from the file's records.
    """
    data: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
    return [to_ticket(datum, data_service) for datum in data]
