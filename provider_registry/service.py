from sqlalchemy.orm import Session

from provider_registry.models import ProviderRecord
from provider_registry.repository import ProviderRepository
from provider_registry.schemas import CapabilityMatrix, ProviderRead, ProviderUpdate
from provider_registry.seed import seed_providers


class ProviderRegistryService:
    def __init__(self, repository: ProviderRepository) -> None:
        self.repository = repository

    @classmethod
    def from_session(cls, db: Session) -> "ProviderRegistryService":
        return cls(ProviderRepository(db))

    def ensure_seeded(self) -> None:
        desired = {provider.id: provider for provider in seed_providers()}
        existing = {provider.id: provider for provider in self.repository.list()}
        for provider_id in set(existing) - set(desired):
            record = self.repository.db.get(ProviderRecord, provider_id)
            if record is not None:
                self.repository.db.delete(record)
        self.repository.db.commit()
        for provider_id, provider in desired.items():
            if provider_id not in existing:
                self.repository.create(provider)
                continue
            self.repository.update(
                provider_id,
                ProviderUpdate.model_validate(provider.model_dump(exclude={"id"})),
            )

    def list(self) -> list[ProviderRead]:
        self.ensure_seeded()
        return self.repository.list()

    def get(self, provider_id: str) -> ProviderRead:
        self.ensure_seeded()
        return self.repository.get(provider_id)

    def capabilities(self) -> CapabilityMatrix:
        providers = self.list()
        matrix: dict[str, list[str]] = {}
        for provider in providers:
            for capability in provider.capabilities:
                matrix.setdefault(capability, []).append(provider.id)
        return CapabilityMatrix(
            capabilities={key: sorted(value) for key, value in sorted(matrix.items())},
            providers=len(providers),
        )
