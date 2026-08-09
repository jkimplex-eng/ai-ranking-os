from backend.app.providers.ollama import OllamaProvider
from backend.app.providers.provider import ConfiguredProvider
from backend.app.providers.registry import ProviderRegistry, registry


class ProviderFactory:
    def __init__(self, provider_registry: ProviderRegistry = registry) -> None:
        self.registry = provider_registry

    def create(self, provider: str) -> ConfiguredProvider | OllamaProvider:
        if provider.casefold() == "ollama":
            return OllamaProvider()
        return ConfiguredProvider(self.registry.get(provider), provider_registry=self.registry)

    def all(self) -> list[ConfiguredProvider]:
        return [
            ConfiguredProvider(definition, provider_registry=self.registry)
            for definition in self.registry.all()
        ]


factory = ProviderFactory()

