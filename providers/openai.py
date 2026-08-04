from providers.base import BaseMockProvider


class OpenAIProvider(BaseMockProvider):
    provider_name = "openai"
    credential_env = "OPENAI_API_KEY"

