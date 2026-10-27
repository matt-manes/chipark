from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TicketStatus(Enum):
    """Represent the lifecycle status of a ticket."""

    OPEN = 1
    CLOSED = 2


@dataclass
class Ticket:
    """
    Represent a maintenance ticket associated with a park.

    Attributes
    ----------
    park_name : str
        Name of the park associated with the ticket.
    status : TicketStatus
        Current ticket status.
    file_date : datetime
        Date and time when the ticket was filed.
    estimated_hours : float or None
        Estimated work duration in hours, if available.
    issue : str
        Description of the reported issue.
    ticket_id : int, default=-1
        Database identifier; negative values indicate an unpersisted ticket.
    """

    park_name: str
    status: TicketStatus
    file_date: datetime
    estimated_hours: float | None
    issue: str
    ticket_id: int = -1
