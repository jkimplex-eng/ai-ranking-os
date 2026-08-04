from providers.base import BaseMockProvider


class AnthropicProvider(BaseMockProvider):
    provider_name = "anthropic"
    credential_env = "ANTHROPIC_API_KEY"

