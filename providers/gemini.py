from providers.base import BaseMockProvider


class GeminiProvider(BaseMockProvider):
    provider_name = "gemini"
    credential_env = "GEMINI_API_KEY"

