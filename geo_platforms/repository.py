from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from geo_platforms.models import GeoPlatform, GeoPlatformImport


class PlatformRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, platform_id: UUID) -> GeoPlatform | None:
        return self.db.get(GeoPlatform, platform_id)

    def by_domain(self, domain: str) -> GeoPlatform | None:
        return self.db.scalar(select(GeoPlatform).where(GeoPlatform.domain == domain))

    def list(
        self, *, category: str | None = None, language: str | None = None
    ) -> list[GeoPlatform]:
        statement = select(GeoPlatform)
        if category:
            statement = statement.where(GeoPlatform.category == category)
        if language:
            statement = statement.where(GeoPlatform.language == language)
        return list(self.db.scalars(statement.order_by(GeoPlatform.name, GeoPlatform.domain)))

    def save(self, item: GeoPlatform) -> GeoPlatform:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item: GeoPlatform) -> None:
        self.db.delete(item)
        self.db.commit()

    def save_import(self, item: GeoPlatformImport) -> GeoPlatformImport:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
