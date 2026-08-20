from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from competitor_intelligence.models import (
    CompetitorDailySnapshot,
    CompetitorPublicationObservation,
    CompetitorSocialPost,
    CompetitorSocialSource,
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

    def add_social_source(self, item: CompetitorSocialSource) -> CompetitorSocialSource:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def social_source(self, source_id: int) -> CompetitorSocialSource | None:
        return self.db.get(CompetitorSocialSource, source_id)

    def social_sources(self, competitor_id: int) -> list[CompetitorSocialSource]:
        return list(
            self.db.scalars(
                select(CompetitorSocialSource)
                .where(CompetitorSocialSource.competitor_id == competitor_id)
                .order_by(CompetitorSocialSource.created_at)
            )
        )

    def due_social_sources(self, now) -> list[CompetitorSocialSource]:
        return list(
            self.db.scalars(
                select(CompetitorSocialSource).where(
                    CompetitorSocialSource.active.is_(True),
                    (
                        CompetitorSocialSource.next_scan_at.is_(None)
                        | (CompetitorSocialSource.next_scan_at <= now)
                    ),
                )
            )
        )

    def social_post(self, source_id: int, external_post_id: str) -> CompetitorSocialPost | None:
        return self.db.scalar(
            select(CompetitorSocialPost).where(
                CompetitorSocialPost.source_id == source_id,
                CompetitorSocialPost.external_post_id == external_post_id,
            )
        )

    def social_posts(self, source_id: int, limit: int = 50) -> list[CompetitorSocialPost]:
        return list(
            self.db.scalars(
                select(CompetitorSocialPost)
                .where(CompetitorSocialPost.source_id == source_id)
                .order_by(CompetitorSocialPost.published_at.desc())
                .limit(limit)
            )
        )

    def delete_social_source(self, item: CompetitorSocialSource) -> None:
        self.db.delete(item)
        self.db.commit()
