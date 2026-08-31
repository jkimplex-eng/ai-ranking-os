from sqlalchemy import select
from sqlalchemy.orm import Session

from yandex_wordstat.models import WordstatConnection, WordstatDemandSnapshot


class WordstatRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def connection(self, organization_id: int) -> WordstatConnection | None:
        return self.db.scalar(
            select(WordstatConnection).where(WordstatConnection.organization_id == organization_id)
        )

    def latest(
        self, organization_id: int, brand: str | None = None
    ) -> WordstatDemandSnapshot | None:
        statement = select(WordstatDemandSnapshot).where(
            WordstatDemandSnapshot.organization_id == organization_id
        )
        if brand:
            statement = statement.where(WordstatDemandSnapshot.brand.ilike(brand))
        return self.db.scalar(
            statement.order_by(
                WordstatDemandSnapshot.created_at.desc(), WordstatDemandSnapshot.id.desc()
            ).limit(1)
        )

    def save(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item) -> None:
        self.db.delete(item)
        self.db.commit()
