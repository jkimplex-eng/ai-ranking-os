from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eis.models import EISScore


class EISRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, score: EISScore) -> EISScore:
        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)
        return score

    def get(self, score_id: UUID) -> EISScore | None:
        return self.db.get(EISScore, score_id)

    def history(self, platform_id: UUID, limit: int = 100) -> list[EISScore]:
        return list(
            self.db.scalars(
                select(EISScore)
                .where(EISScore.platform_id == platform_id)
                .order_by(EISScore.calculated_at.desc())
                .limit(limit)
            )
        )
