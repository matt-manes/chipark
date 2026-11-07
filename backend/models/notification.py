from dataclasses import dataclass
from datetime import datetime
from enum import Enum

MAX_NOTIFICATIONS_PER_REQUEST: int = 100


class NotificationEventType(str, Enum):
    """Represent ticket events that are delivered to notification recipients."""

    TICKET_UPDATED = "ticket_updated"
    TICKET_CLOSED = "ticket_closed"
    TICKET_DELETED = "ticket_deleted"


@dataclass
class Notification:
    """Represent a persisted notification for a ticket submitter.

    Attributes
    ----------
    notification_id : int
        Stable identifier used as the SSE event ID and reconnect cursor.
    event_type : NotificationEventType
        Ticket event that caused this notification.
    ticket_id : int
        Identifier of the ticket, retained after ticket deletion.
    park_name : str
        Park associated with the ticket when the event occurred.
    issue : str
        Issue description when the event occurred.
    created_at : datetime
        Time the notification was created.
    read_at : datetime or None
        Time the recipient read the notification, if applicable.
    """

    notification_id: int
    event_type: NotificationEventType
    ticket_id: int
    park_name: str
    issue: str
    created_at: datetime
    read_at: datetime | None
