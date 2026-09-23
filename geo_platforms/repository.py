from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from geo_platforms.models import GeoPlatform, GeoPlatformImport


class PlatformRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, platform_id: UUID) -> GeoPlatform | None:
        statement = select(GeoPlatform).where(GeoPlatform.id == platform_id)
        return self.db.scalar(self._scope(statement))

    def by_domain(self, domain: str) -> GeoPlatform | None:
        return self.db.scalar(self._scope(select(GeoPlatform).where(GeoPlatform.domain == domain)))

    def list(
        self, *, category: str | None = None, language: str | None = None
    ) -> list[GeoPlatform]:
        statement = self._scope(select(GeoPlatform))
        if category:
            statement = statement.where(GeoPlatform.category == category)
        if language:
            statement = statement.where(GeoPlatform.language == language)
        return list(self.db.scalars(statement.order_by(GeoPlatform.name, GeoPlatform.domain)))

    def save(self, item: GeoPlatform) -> GeoPlatform:
        if "geo_organization_id" in self.db.info:
            organization_id = self.db.info["geo_organization_id"]
            if item.organization_id is None:
                item.organization_id = organization_id
            elif item.organization_id != organization_id:
                raise PermissionError("Platform belongs to another organization")
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

    def _scope(self, statement):
        if "geo_organization_id" in self.db.info:
            return statement.where(
                GeoPlatform.organization_id == self.db.info["geo_organization_id"]
            )
        return statement
