from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.ticket import Ticket, TicketStatus, TicketUpdate
from .entities import TicketRecord


class TicketRepository:
    """Persist and retrieve tickets using a SQLAlchemy session factory."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """
        Create a repository using the given session factory.

        Parameters
        ----------
        session_factory : sessionmaker[Session]
            Factory bound to the database where ticket records are stored.
        """
        self._session_factory: sessionmaker[Session] = session_factory

    def add(self, ticket: Ticket) -> Ticket:
        """
        Persist a ticket and return it with its database identifier.

        Parameters
        ----------
        ticket : Ticket
            Ticket to add.

        Returns
        -------
        Ticket
            Persisted ticket model.
        """
        with self._session_factory.begin() as session:
            record = TicketRecord(
                ticket_id=ticket.ticket_id if ticket.ticket_id >= 0 else None,
                park_name=ticket.park_name,
                status=ticket.status,
                file_date=ticket.file_date,
                estimated_hours=ticket.estimated_hours,
                issue=ticket.issue,
                user_id=ticket.user_id,
            )
            session.add(record)
            session.flush()
            return self._to_model(record)

    def get(self, ticket_id: int) -> Ticket:
        """
        Retrieve a ticket by its database identifier.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to retrieve.

        Returns
        -------
        Ticket
            Matching persisted ticket.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        with self._session_factory() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            return self._to_model(record)

    def get_all(self) -> list[Ticket]:
        """
        Retrieve all tickets ordered by database identifier.

        Returns
        -------
        list[Ticket]
            Persisted tickets in identifier order.
        """
        with self._session_factory() as session:
            records: Sequence[TicketRecord] = session.scalars(
                select(TicketRecord).order_by(TicketRecord.ticket_id)
            ).all()
            return [self._to_model(record) for record in records]

    def close(self, ticket_id: int) -> Ticket:
        """
        Mark a ticket as closed and return the updated model.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to close.

        Returns
        -------
        Ticket
            Updated ticket with closed status.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        with self._session_factory.begin() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            record.status = TicketStatus.CLOSED
            session.flush()
            return self._to_model(record)

    def update(self, ticket_id: int, changes: TicketUpdate) -> Ticket:
        """Update editable fields and return the persisted ticket.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to update.
        changes : TicketUpdate
            Validated fields to change.

        Returns
        -------
        Ticket
            Updated ticket.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        ValueError
            If a non-nullable editable field is set to ``None``.
        """
        with self._session_factory.begin() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            for field_name, value in changes.model_dump(exclude_unset=True).items():
                if field_name == "issue" and value is None:
                    raise ValueError("A ticket issue cannot be null.")
                setattr(record, field_name, value)
            session.flush()
            return self._to_model(record)

    def delete(self, ticket_id: int) -> None:
        """Delete a ticket.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to delete.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        with self._session_factory.begin() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            session.delete(record)

    @staticmethod
    def _to_model(record: TicketRecord) -> Ticket:
        """
        Convert a database record to a ticket model.

        Parameters
        ----------
        record : TicketRecord
            Database record to convert.

        Returns
        -------
        Ticket
            Ticket model represented by the record.
        """
        return Ticket(
            park_name=record.park_name,
            status=record.status,
            file_date=record.file_date,
            estimated_hours=record.estimated_hours,
            issue=record.issue,
            ticket_id=record.ticket_id,
            user_id=record.user_id,
        )
