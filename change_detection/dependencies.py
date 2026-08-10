from sqlalchemy.orm import Session

from change_detection.repository import ChangeRepository
from change_detection.service import ChangeDetectionService
from notification_center.ports import NotificationPort
from research.change_detection_adapter import ResearchChangeSnapshotSource


def build_change_detection(
    db: Session, notifications: NotificationPort | None = None
) -> ChangeDetectionService:
    return ChangeDetectionService(
        ChangeRepository(db), ResearchChangeSnapshotSource(db), notifications
    )
