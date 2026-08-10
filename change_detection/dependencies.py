from sqlalchemy.orm import Session

from change_detection.repository import ChangeRepository
from change_detection.service import ChangeDetectionService
from research.change_detection_adapter import ResearchChangeSnapshotSource


def build_change_detection(db: Session) -> ChangeDetectionService:
    return ChangeDetectionService(ChangeRepository(db), ResearchChangeSnapshotSource(db))
