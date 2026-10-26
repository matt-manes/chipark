from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.ticket import Ticket, TicketStatus
from .entities import TicketRecord


class TicketRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory: sessionmaker[Session] = session_factory

    def add(self, ticket: Ticket) -> Ticket:
        with self._session_factory.begin() as session:
            record = TicketRecord(
                ticket_id=ticket.ticket_id if ticket.ticket_id >= 0 else None,
                park_name=ticket.park_name,
                status=ticket.status,
                file_date=ticket.file_date,
                estimated_hours=ticket.estimated_hours,
                issue=ticket.issue,
            )
            session.add(record)
            session.flush()
            return self._to_model(record)

    def get(self, ticket_id: int) -> Ticket:
        with self._session_factory() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            return self._to_model(record)

    def get_all(self) -> list[Ticket]:
        with self._session_factory() as session:
            records: Sequence[TicketRecord] = session.scalars(
                select(TicketRecord).order_by(TicketRecord.ticket_id)
            ).all()
            return [self._to_model(record) for record in records]

    def close(self, ticket_id: int) -> Ticket:
        with self._session_factory.begin() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            record.status = TicketStatus.CLOSED
            session.flush()
            return self._to_model(record)

    @staticmethod
    def _to_model(record: TicketRecord) -> Ticket:
        return Ticket(
            park_name=record.park_name,
            status=record.status,
            file_date=record.file_date,
            estimated_hours=record.estimated_hours,
            issue=record.issue,
            ticket_id=record.ticket_id,
        )
