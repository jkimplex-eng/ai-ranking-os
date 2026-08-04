from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apikeys.models import ApiKey


class ApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, key: ApiKey) -> ApiKey:
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        return key

    def get(self, key_id: int) -> ApiKey | None:
        return self.db.get(ApiKey, key_id)

    def by_prefix(self, prefix: str) -> ApiKey | None:
        return self.db.scalar(select(ApiKey).where(ApiKey.prefix == prefix))

    def list(self, owner_id: int | None = None) -> list[ApiKey]:
        query = select(ApiKey).order_by(ApiKey.id.desc())
        if owner_id is not None:
            query = query.where(ApiKey.owner_id == owner_id)
        return list(self.db.scalars(query))
