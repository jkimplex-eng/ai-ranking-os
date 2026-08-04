from providers.anthropic import AnthropicProvider
from providers.base import BaseMockProvider, ProviderRequest, ProviderResponse
from providers.deepseek import DeepSeekProvider
from providers.gemini import GeminiProvider
from providers.grok import GrokProvider
from providers.local import LocalProvider
from providers.mistral import MistralProvider
from providers.openai import OpenAIProvider
from providers.perplexity import PerplexityProvider

PROVIDER_CLASSES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "perplexity": PerplexityProvider,
    "mistral": MistralProvider,
    "grok": GrokProvider,
    "local": LocalProvider,
}


def create_provider(provider: str) -> BaseMockProvider:
    provider_class = PROVIDER_CLASSES.get(provider.casefold())
    if provider_class is None:
        raise KeyError(f"Unsupported provider: {provider}")
    return provider_class()


__all__ = [
    "BaseMockProvider",
    "ProviderRequest",
    "ProviderResponse",
    "create_provider",
]

