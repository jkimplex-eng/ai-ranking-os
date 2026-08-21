from sqlalchemy import select
from sqlalchemy.orm import Session

from yandex_intelligence.models import YandexIntelligenceSnapshot


class YandexIntelligenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, item: YandexIntelligenceSnapshot) -> YandexIntelligenceSnapshot:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def latest(self, organization_id: int) -> YandexIntelligenceSnapshot | None:
        return self.db.scalar(
            select(YandexIntelligenceSnapshot)
            .where(YandexIntelligenceSnapshot.organization_id == organization_id)
            .order_by(
                YandexIntelligenceSnapshot.created_at.desc(), YandexIntelligenceSnapshot.id.desc()
            )
            .limit(1)
        )
