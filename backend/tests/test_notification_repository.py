import pytest

from backend.models.notification import Notification, NotificationEventType
from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus, TicketUpdate
from backend.models.user import User
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.park_repository import ParkRepository
from backend.repositories.ticket_repository import TicketRepository


def test_ticket_update_creates_notification_for_submitter(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    ticket_repository.update(
        saved_ticket.ticket_id, TicketUpdate(issue="Updated bench")
    )

    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )
    assert len(notifications) == 1
    assert notifications[0].event_type is NotificationEventType.TICKET_UPDATED
    assert notifications[0].ticket_id == saved_ticket.ticket_id
    assert notifications[0].issue == "Updated bench"


def test_ticket_delete_creates_notification_with_ticket_summary(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    ticket_repository.delete(saved_ticket.ticket_id)

    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )
    assert len(notifications) == 1
    assert notifications[0].event_type is NotificationEventType.TICKET_DELETED
    assert notifications[0].ticket_id == saved_ticket.ticket_id
    assert notifications[0].park_name == saved_ticket.park_name
    assert notifications[0].issue == saved_ticket.issue


def test_ticket_close_creates_notification(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    closed_ticket: Ticket = ticket_repository.close(saved_ticket.ticket_id)

    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )
    assert closed_ticket.status is TicketStatus.CLOSED
    assert len(notifications) == 1
    assert notifications[0].event_type is NotificationEventType.TICKET_CLOSED


def test_mark_read_records_read_timestamp(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)
    ticket_repository.update(
        saved_ticket.ticket_id, TicketUpdate(issue="Updated bench")
    )
    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )

    notification: Notification = notification_repository.mark_read(
        sample_user.user_id, notifications[0].notification_id
    )

    assert notification.read_at is not None


def test_mark_read_rejects_another_users_notification(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)
    ticket_repository.update(
        saved_ticket.ticket_id, TicketUpdate(issue="Updated bench")
    )
    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )
    notification_id: int = notifications[0].notification_id

    with pytest.raises(LookupError):
        notification_repository.mark_read(sample_user.user_id + 1, notification_id)


def test_get_after_returns_only_notifications_after_cursor(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)
    ticket_repository.update(saved_ticket.ticket_id, TicketUpdate(issue="First update"))
    ticket_repository.update(
        saved_ticket.ticket_id, TicketUpdate(issue="Second update")
    )
    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )
    cursor: int = min(notification.notification_id for notification in notifications)

    result: list[Notification] = notification_repository.get_after(
        sample_user.user_id, cursor
    )

    assert len(result) == 1
    assert result[0].notification_id > cursor
    assert result[0].issue == "Second update"


def test_get_after_does_not_return_another_users_notifications(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)
    ticket_repository.update(
        saved_ticket.ticket_id, TicketUpdate(issue="Ticket updated")
    )

    result: list[Notification] = notification_repository.get_after(
        sample_user.user_id + 1, 0
    )

    assert result == []


def test_get_latest_id_for_user_returns_latest_notification(
    notification_repository: NotificationRepository,
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
    sample_user: User,
) -> None:
    park_repository.add(sample_park)
    sample_ticket.user_id = sample_user.user_id
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)
    ticket_repository.update(saved_ticket.ticket_id, TicketUpdate(issue="First update"))
    ticket_repository.update(
        saved_ticket.ticket_id, TicketUpdate(issue="Second update")
    )
    notifications: list[Notification] = notification_repository.get_for_user(
        sample_user.user_id
    )

    latest_id: int = notification_repository.get_latest_id_for_user(sample_user.user_id)

    assert latest_id == max(
        notification.notification_id for notification in notifications
    )


def test_get_latest_id_for_user_returns_zero_without_notifications(
    notification_repository: NotificationRepository,
    sample_user: User,
) -> None:
    latest_id: int = notification_repository.get_latest_id_for_user(sample_user.user_id)

    assert latest_id == 0
