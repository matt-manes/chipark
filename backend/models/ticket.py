from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


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
    user_id : int or None, default=None
        Identifier of the account that submitted the ticket, if available.
    ticket_id : int, default=-1
        Database identifier; negative values indicate an unpersisted ticket.
    """

    park_name: str
    status: TicketStatus
    file_date: datetime
    estimated_hours: float | None
    issue: str
    ticket_id: int = -1
    user_id: int | None = None


class TicketSubmission(BaseModel):
    """Represent the fields accepted when submitting a new ticket.

    Attributes
    ----------
    park_name : str
        Exact name of an existing park.
    estimated_hours : float or None, default=None
        Estimated repair duration, if known.
    issue : str
        User-submitted description of the issue.
    """

    park_name: str
    estimated_hours: float | None = None
    issue: str


class TicketUpdate(BaseModel):
    """Validate fields accepted for administrative ticket updates.

    Attributes
    ----------
    estimated_hours : float or None, optional
        Updated work estimate, or ``None`` to clear it.
    issue : str or None, optional
        Updated issue description.
    status : TicketStatus or None, optional
        Updated status.
    """

    model_config = ConfigDict(extra="forbid")

    estimated_hours: float | None = None
    issue: str | None = None
    status: TicketStatus | None = None
