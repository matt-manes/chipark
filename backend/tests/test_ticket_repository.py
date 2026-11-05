import pytest

from backend.models.park import Park
from backend.models.ticket import Ticket, TicketStatus, TicketUpdate
from backend.repositories.park_repository import ParkRepository
from backend.repositories.ticket_repository import TicketRepository


def test_add_assigns_generated_id(
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
) -> None:
    park_repository.add(sample_park)
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    assert saved_ticket.ticket_id > 0


def test_get_returns_saved_ticket(
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
) -> None:
    park_repository.add(sample_park)
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    assert ticket_repository.get(saved_ticket.ticket_id) == saved_ticket


def test_get_raises_for_missing_ticket(
    ticket_repository: TicketRepository,
) -> None:
    with pytest.raises(LookupError, match="Ticket 42 was not found"):
        ticket_repository.get(42)


def test_get_all_returns_tickets_in_id_order(
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
) -> None:
    park_repository.add(sample_park)
    first_ticket: Ticket = ticket_repository.add(sample_ticket)
    second_ticket: Ticket = ticket_repository.add(
        Ticket(
            park_name=sample_ticket.park_name,
            status=TicketStatus.OPEN,
            file_date=sample_ticket.file_date,
            estimated_hours=1.0,
            issue="Damaged sign",
        )
    )

    assert ticket_repository.get_all() == [first_ticket, second_ticket]


def test_close_persists_closed_status(
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
) -> None:
    park_repository.add(sample_park)
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    closed_ticket: Ticket = ticket_repository.close(saved_ticket.ticket_id)

    assert closed_ticket.status is TicketStatus.CLOSED
    assert ticket_repository.get(saved_ticket.ticket_id).status is TicketStatus.CLOSED


def test_close_raises_for_missing_ticket(
    ticket_repository: TicketRepository,
) -> None:
    with pytest.raises(LookupError, match="Ticket 42 was not found"):
        ticket_repository.close(42)


def test_update_raises_for_missing_ticket(
    ticket_repository: TicketRepository,
) -> None:
    with pytest.raises(LookupError, match="Ticket 42 was not found"):
        ticket_repository.update(42, TicketUpdate(issue="Updated issue"))


def test_update_rejects_empty_issue(
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
) -> None:
    park_repository.add(sample_park)
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    with pytest.raises(ValueError, match="issue cannot be empty"):
        ticket_repository.update(saved_ticket.ticket_id, TicketUpdate(issue=""))


def test_update_rejects_null_issue(
    park_repository: ParkRepository,
    ticket_repository: TicketRepository,
    sample_park: Park,
    sample_ticket: Ticket,
) -> None:
    park_repository.add(sample_park)
    saved_ticket: Ticket = ticket_repository.add(sample_ticket)

    with pytest.raises(ValueError, match="issue cannot be null"):
        ticket_repository.update(saved_ticket.ticket_id, TicketUpdate(issue=None))


def test_delete_raises_for_missing_ticket(
    ticket_repository: TicketRepository,
) -> None:
    with pytest.raises(LookupError, match="Ticket 42 was not found"):
        ticket_repository.delete(42)
