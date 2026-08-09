from datetime import UTC, datetime

from sqlalchemy.orm import Session

from provider_discovery.models import ProviderSyncRun
from provider_discovery.ports import ProviderCatalogSource
from provider_discovery.source import HttpProviderCatalogSource
from provider_registry.repository import ProviderNotFoundError, ProviderRepository
from provider_registry.schemas import ProviderUpdate


class ProviderDiscoveryService:
    def __init__(self, db: Session, source: ProviderCatalogSource | None = None) -> None:
        self.db = db
        self.source = source or HttpProviderCatalogSource()
        self.repository = ProviderRepository(db)

    def sync(self) -> ProviderSyncRun:
        created = updated = 0
        source_name = getattr(self.source, "url", type(self.source).__name__)
        now = datetime.now(UTC)
        try:
            providers = self.source.fetch()
            for payload in providers:
                try:
                    self.repository.get(payload.id)
                except ProviderNotFoundError:
                    self.repository.create(payload)
                    created += 1
                else:
                    self.repository.update(
                        payload.id,
                        ProviderUpdate(**payload.model_dump(exclude={"id"})),
                    )
                    updated += 1
            run = ProviderSyncRun(
                source=str(source_name),
                status="COMPLETED",
                discovered=len(providers),
                created=created,
                updated=updated,
                created_at=now,
            )
        except Exception as error:
            run = ProviderSyncRun(
                source=str(source_name),
                status="FAILED",
                discovered=0,
                created=0,
                updated=0,
                error=str(error),
                created_at=now,
            )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
