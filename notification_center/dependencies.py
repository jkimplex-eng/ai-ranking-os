from sqlalchemy.orm import Session

from notification_center.repository import NotificationRepository
from notification_center.service import NotificationService


def build_notification_service(db: Session) -> NotificationService:
    return NotificationService(NotificationRepository(db))
