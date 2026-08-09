from typing import Protocol

from provider_registry.schemas import ProviderCreate


class ProviderCatalogSource(Protocol):
    def fetch(self) -> list[ProviderCreate]: ...
