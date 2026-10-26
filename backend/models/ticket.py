from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TicketStatus(Enum):
    OPEN = 1
    CLOSED = 2


@dataclass
class Ticket:
    park_name: str
    status: TicketStatus
    file_date: datetime
    estimated_hours: float | None
    issue: str
    ticket_id: int = -1
