from sqlalchemy import select
from sqlalchemy.orm import Session

from change_detection.models import ResearchChange


class ChangeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, research_id: int) -> ResearchChange | None:
        return self.db.scalar(
            select(ResearchChange).where(ResearchChange.research_id == research_id)
        )

    def save(self, change: ResearchChange) -> ResearchChange:
        self.db.add(change)
        self.db.commit()
        self.db.refresh(change)
        return change
