from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from provider_registry.models import ProviderRecord
from provider_registry.schemas import ProviderCreate, ProviderRead, ProviderUpdate


class ProviderNotFoundError(LookupError):
    pass


class ProviderConflictError(RuntimeError):
    pass


class ProviderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[ProviderRead]:
        records = self.db.scalars(
            select(ProviderRecord).order_by(ProviderRecord.priority, ProviderRecord.id)
        )
        return [self._read(record) for record in records]

    def get(self, provider_id: str) -> ProviderRead:
        record = self.db.get(ProviderRecord, provider_id.casefold())
        if record is None:
            raise ProviderNotFoundError(f"Provider {provider_id} was not found")
        return self._read(record)

    def create(self, payload: ProviderCreate) -> ProviderRead:
        if self.db.get(ProviderRecord, payload.id) is not None:
            raise ProviderConflictError(f"Provider {payload.id} already exists")
        now = datetime.now(UTC)
        data = payload.model_dump(mode="json")
        metadata = data.pop("metadata")
        record = ProviderRecord(**data, metadata_payload=metadata, created_at=now, updated_at=now)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._read(record)

    def update(self, provider_id: str, payload: ProviderUpdate) -> ProviderRead:
        record = self.db.get(ProviderRecord, provider_id.casefold())
        if record is None:
            raise ProviderNotFoundError(f"Provider {provider_id} was not found")
        changes = payload.model_dump(exclude_unset=True, mode="json")
        if "metadata" in changes:
            changes["metadata_payload"] = changes.pop("metadata")
        for field, value in changes.items():
            setattr(record, field, value)
        record.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(record)
        return self._read(record)

    def _read(self, record: ProviderRecord) -> ProviderRead:
        return ProviderRead.model_validate(
            {
                **record.__dict__,
                "metadata": record.metadata_payload,
            }
        )
