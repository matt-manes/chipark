from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models.notification import NotificationEventType
from ..models.ticket import Ticket, TicketStatus, TicketUpdate
from ..tools.accent_normalizer import AccentNormalizer
from .entities import NotificationRecord, TicketRecord, UserRecord


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
                park_name=AccentNormalizer.remove_accents(ticket.park_name),
                status=ticket.status,
                file_date=ticket.file_date,
                estimated_hours=ticket.estimated_hours,
                issue=AccentNormalizer.remove_accents(ticket.issue),
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

    def get_for_user(self, user_id: int) -> list[Ticket]:
        """Retrieve tickets submitted by one user, ordered by identifier.

        Parameters
        ----------
        user_id : int
            Submitter account identifier.

        Returns
        -------
        list[Ticket]
            Tickets submitted by the requested account.
        """
        with self._session_factory() as session:
            records: Sequence[TicketRecord] = session.scalars(
                select(TicketRecord)
                .where(TicketRecord.user_id == user_id)
                .order_by(TicketRecord.ticket_id)
            ).all()
            return [self._to_model(record) for record in records]

    def get_open_for_park(self, park_name: str) -> list[Ticket]:
        """Retrieve open tickets for one park, ordered by identifier.

        Parameters
        ----------
        park_name : str
            Park name associated with the requested tickets.

        Returns
        -------
        list[Ticket]
            Open tickets for the requested park.
        """
        with self._session_factory() as session:
            records: Sequence[TicketRecord] = session.scalars(
                select(TicketRecord)
                .where(
                    TicketRecord.park_name == park_name,
                    TicketRecord.status == TicketStatus.OPEN,
                )
                .order_by(TicketRecord.ticket_id)
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
            was_open: bool = record.status is not TicketStatus.CLOSED
            record.status = TicketStatus.CLOSED
            if was_open:
                self._add_notification(
                    session, record, NotificationEventType.TICKET_CLOSED
                )
            session.flush()
            return self._to_model(record)

    def reopen(self, ticket_id: int) -> Ticket:
        """Mark a ticket as open and notify its submitter when it changes.

        Parameters
        ----------
        ticket_id : int
            Identifier of the ticket to reopen.

        Returns
        -------
        Ticket
            Updated ticket with open status.

        Raises
        ------
        LookupError
            If no ticket has the requested identifier.
        """
        with self._session_factory.begin() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            was_closed: bool = record.status is not TicketStatus.OPEN
            record.status = TicketStatus.OPEN
            if was_closed:
                self._add_notification(
                    session, record, NotificationEventType.TICKET_REOPENED
                )
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
            If the issue is null or empty.
        """
        with self._session_factory.begin() as session:
            record: TicketRecord | None = session.get(TicketRecord, ticket_id)
            if record is None:
                raise LookupError(f"Ticket {ticket_id} was not found")
            has_changes: bool = False
            previous_status: TicketStatus = record.status
            for field_name, value in changes.model_dump(exclude_unset=True).items():
                if field_name == "issue":
                    if value is None:
                        raise ValueError("A ticket issue cannot be null.")
                    if not isinstance(value, str):
                        raise ValueError("A ticket issue must be text.")
                    if not value.strip():
                        raise ValueError("A ticket issue cannot be empty.")
                    value = AccentNormalizer.remove_accents(value)
                if field_name == "status" and value is None:
                    raise ValueError("A ticket status cannot be null.")
                if getattr(record, field_name) != value:
                    has_changes = True
                setattr(record, field_name, value)
            if has_changes:
                event_type: NotificationEventType = NotificationEventType.TICKET_UPDATED
                if previous_status is not record.status:
                    event_type = (
                        NotificationEventType.TICKET_CLOSED
                        if record.status is TicketStatus.CLOSED
                        else NotificationEventType.TICKET_REOPENED
                    )
                self._add_notification(session, record, event_type)
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
            self._add_notification(
                session, record, NotificationEventType.TICKET_DELETED
            )
            session.delete(record)

    @staticmethod
    def _add_notification(
        session: Session,
        record: TicketRecord,
        event_type: NotificationEventType,
    ) -> None:
        """Create a recipient notification within the ticket transaction.

        Parameters
        ----------
        session : Session
            Active transaction containing the ticket change.
        record : TicketRecord
            Ticket state to preserve in the notification.
        event_type : NotificationEventType
            Event that caused the notification.
        """
        if record.user_id is None:
            return
        # Keep notification IDs ordered by commit for a user's SSE cursor.
        session.scalar(
            select(UserRecord.user_id)
            .where(UserRecord.user_id == record.user_id)
            .with_for_update()
        )
        session.add(
            NotificationRecord(
                user_id=record.user_id,
                event_type=event_type.value,
                ticket_id=record.ticket_id,
                park_name=record.park_name,
                issue=record.issue,
                created_at=datetime.now(),
            )
        )

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
