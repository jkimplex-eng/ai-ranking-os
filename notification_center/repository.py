from sqlalchemy import select
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

    def list(self, user_id: int, unread_only: bool = False) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))
        return list(self.db.scalars(statement.order_by(Notification.created_at.desc())))

    def deliveries(self, notification_id: int) -> list[NotificationDelivery]:
        return list(
            self.db.scalars(
                select(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notification_id
                )
            )
        )
