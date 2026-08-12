from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_lab.models import PublicationObservation, ResearchPublication
from research_lab.schemas import ObservationCreate, PublicationCreate


class PublicationNotFoundError(LookupError):
    pass


class PublicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: PublicationCreate) -> ResearchPublication:
        item = ResearchPublication(**payload.model_dump(exclude={"url"}), url=str(payload.url))
        self.db.add(item)
        self.db.commit()
        return self.get(item.id)

    def get(self, publication_id: int) -> ResearchPublication:
        item = self.db.scalar(
            select(ResearchPublication)
            .options(selectinload(ResearchPublication.observations))
            .where(ResearchPublication.id == publication_id)
        )
        if item is None:
            raise PublicationNotFoundError(f"Publication {publication_id} not found")
        return item

    def list_for_entity(self, entity_id: UUID) -> list[ResearchPublication]:
        return list(
            self.db.scalars(
                select(ResearchPublication)
                .options(selectinload(ResearchPublication.observations))
                .where(ResearchPublication.entity_id == entity_id)
                .order_by(ResearchPublication.published_at.desc(), ResearchPublication.id.desc())
            )
        )

    def record_observation(
        self, publication_id: int, payload: ObservationCreate
    ) -> PublicationObservation:
        self.get(publication_id)
        existing = self.db.scalar(
            select(PublicationObservation).where(
                PublicationObservation.publication_id == publication_id,
                PublicationObservation.provider == payload.provider,
                PublicationObservation.model == payload.model,
            )
        )
        if existing is None:
            existing = PublicationObservation(publication_id=publication_id, **payload.model_dump())
            self.db.add(existing)
        elif self._utc(payload.first_observed_at) < self._utc(existing.first_observed_at):
            for key, value in payload.model_dump().items():
                setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)
        return existing

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
