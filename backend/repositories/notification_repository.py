from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ..models.notification import (
    MAX_NOTIFICATIONS_PER_REQUEST,
    Notification,
    NotificationEventType,
)
from .entities import NotificationRecord


class NotificationRepository:
    """Retrieve and update persisted user notifications."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Create a repository using the given session factory.

        Parameters
        ----------
        session_factory : sessionmaker[Session]
            Factory bound to the notification database.
        """
        self._session_factory: sessionmaker[Session] = session_factory

    def get_for_user(
        self, user_id: int, limit: int = MAX_NOTIFICATIONS_PER_REQUEST
    ) -> list[Notification]:
        """Return the newest notifications belonging to one user.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.
        limit : int, default=100
            Maximum number of notifications to return.

        Returns
        -------
        list[Notification]
            Notifications ordered newest first.
        """
        with self._session_factory() as session:
            records: list[NotificationRecord] = list(
                session.scalars(
                    select(NotificationRecord)
                    .where(NotificationRecord.user_id == user_id)
                    .order_by(NotificationRecord.notification_id.desc())
                    .limit(limit)
                ).all()
            )
            return [self._to_model(record) for record in records]

    def get_after(
        self,
        user_id: int,
        notification_id: int,
        limit: int = MAX_NOTIFICATIONS_PER_REQUEST,
    ) -> list[Notification]:
        """Return notifications newer than a user's SSE event cursor.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.
        notification_id : int
            Last event ID acknowledged by the client.
        limit : int, default=100
            Maximum number of notifications to return.

        Returns
        -------
        list[Notification]
            Notifications ordered oldest first.
        """
        with self._session_factory() as session:
            records: list[NotificationRecord] = list(
                session.scalars(
                    select(NotificationRecord)
                    .where(
                        NotificationRecord.user_id == user_id,
                        NotificationRecord.notification_id > notification_id,
                    )
                    .order_by(NotificationRecord.notification_id)
                    .limit(limit)
                ).all()
            )
            return [self._to_model(record) for record in records]

    def get_latest_id_for_user(self, user_id: int) -> int:
        """Return the newest notification ID belonging to a user.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.

        Returns
        -------
        int
            Newest notification ID, or zero when no notification exists.
        """
        with self._session_factory() as session:
            latest_id: int | None = session.scalar(
                select(func.max(NotificationRecord.notification_id)).where(
                    NotificationRecord.user_id == user_id
                )
            )
            return latest_id or 0

    def mark_read(self, user_id: int, notification_id: int) -> Notification:
        """Mark one of the user's notifications as read.

        Parameters
        ----------
        user_id : int
            Identifier of the recipient.
        notification_id : int
            Identifier of the notification to mark as read.

        Returns
        -------
        Notification
            Updated notification.

        Raises
        ------
        LookupError
            If the notification does not belong to the user or does not exist.
        """
        with self._session_factory.begin() as session:
            record: NotificationRecord | None = session.scalar(
                select(NotificationRecord).where(
                    NotificationRecord.notification_id == notification_id,
                    NotificationRecord.user_id == user_id,
                )
            )
            if record is None:
                raise LookupError(f"Notification {notification_id} was not found")
            if record.read_at is None:
                record.read_at = datetime.now()
            session.flush()
            return self._to_model(record)

    @staticmethod
    def _to_model(record: NotificationRecord) -> Notification:
        """Convert a notification record to its public model.

        Parameters
        ----------
        record : NotificationRecord
            Persisted notification record.

        Returns
        -------
        Notification
            Public notification model.
        """
        return Notification(
            notification_id=record.notification_id,
            event_type=NotificationEventType(record.event_type),
            ticket_id=record.ticket_id,
            park_name=record.park_name,
            issue=record.issue,
            created_at=record.created_at,
            read_at=record.read_at,
        )
