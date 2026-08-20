from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from competitor_intelligence.models import (
    CompetitorDailySnapshot,
    CompetitorPublicationObservation,
)


class CompetitorIntelligenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def snapshot(self, competitor_id: int, day: date) -> CompetitorDailySnapshot | None:
        return self.db.scalar(
            select(CompetitorDailySnapshot).where(
                CompetitorDailySnapshot.competitor_id == competitor_id,
                CompetitorDailySnapshot.snapshot_date == day,
            )
        )

    def save_snapshot(self, item: CompetitorDailySnapshot) -> None:
        self.db.add(item)

    def observation_exists(self, competitor_id: int, response_id: int, url: str) -> bool:
        return (
            self.db.scalar(
                select(CompetitorPublicationObservation.id).where(
                    CompetitorPublicationObservation.competitor_id == competitor_id,
                    CompetitorPublicationObservation.response_id == response_id,
                    CompetitorPublicationObservation.url == url,
                )
            )
            is not None
        )

    def add_observation(self, item: CompetitorPublicationObservation) -> None:
        self.db.add(item)

    def snapshots(self, competitor_id: int, limit: int = 90) -> list[CompetitorDailySnapshot]:
        return list(
            self.db.scalars(
                select(CompetitorDailySnapshot)
                .where(CompetitorDailySnapshot.competitor_id == competitor_id)
                .order_by(CompetitorDailySnapshot.snapshot_date.desc())
                .limit(limit)
            )
        )

    def observations(self, competitor_id: int) -> list[CompetitorPublicationObservation]:
        return list(
            self.db.scalars(
                select(CompetitorPublicationObservation)
                .where(CompetitorPublicationObservation.competitor_id == competitor_id)
                .order_by(CompetitorPublicationObservation.last_seen_at.desc())
            )
        )

    def commit(self) -> None:
        self.db.commit()

