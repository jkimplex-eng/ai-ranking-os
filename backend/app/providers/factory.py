from backend.app.providers.ollama import OllamaProvider
from backend.app.providers.provider import ConfiguredProvider
from backend.app.providers.registry import ProviderRegistry, registry


class ProviderFactory:
    def __init__(self, provider_registry: ProviderRegistry = registry) -> None:
        self.registry = provider_registry

    def create(self, provider: str) -> ConfiguredProvider | OllamaProvider:
        canonical = "ollama" if provider.casefold() == "local" else provider.casefold()
        if canonical == "ollama":
            return OllamaProvider()
        return ConfiguredProvider(self.registry.get(canonical), provider_registry=self.registry)

    def all(self) -> list[ConfiguredProvider | OllamaProvider]:
        return [self.create(definition.name) for definition in self.registry.enabled()]


factory = ProviderFactory()

