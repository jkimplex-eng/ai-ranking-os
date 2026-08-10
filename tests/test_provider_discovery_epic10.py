from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from provider_discovery.service import ProviderDiscoveryService
from provider_registry.schemas import ProviderCreate


class FakeCatalog:
    def fetch(self) -> list[ProviderCreate]:
        return [
            ProviderCreate(
                id="free-ai", display_name="Free AI", context_window=8192, free_tier=True
            )
        ]


def test_catalog_sync_creates_then_updates_provider() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        service = ProviderDiscoveryService(db, FakeCatalog())
        first = service.sync()
        second = service.sync()
        assert (first.created, first.updated) == (1, 0)
        assert (second.created, second.updated) == (0, 1)
        assert service.repository.get("free-ai").free_tier is True
    Base.metadata.drop_all(engine)
