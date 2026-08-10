from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from notification_center.models import Notification, NotificationDelivery


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, item: Notification) -> Notification:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_delivery(self, item: NotificationDelivery) -> NotificationDelivery:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(self, user_id: int, notification_id: int) -> Notification | None:
        return self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )

    def list(
        self,
        user_id: int,
        unread_only: bool = False,
        *,
        category: str | None = None,
        priority: str | None = None,
        archived: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))
        statement = statement.where(
            Notification.archived_at.is_not(None)
            if archived
            else Notification.archived_at.is_(None)
        )
        if category:
            statement = statement.where(Notification.category == category)
        if priority:
            statement = statement.where(Notification.priority == priority)
        return list(
            self.db.scalars(
                statement.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
            )
        )

    def counts(self, user_id: int) -> tuple[int, int, int]:
        total = self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.archived_at.is_(None)
            )
        ) or 0
        unread = self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.archived_at.is_(None),
                Notification.is_read.is_(False),
            )
        ) or 0
        archived = self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.archived_at.is_not(None)
            )
        ) or 0
        return unread, total, archived

    def deliveries(self, notification_id: int) -> list[NotificationDelivery]:
        return list(
            self.db.scalars(
                select(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notification_id
                )
            )
        )
