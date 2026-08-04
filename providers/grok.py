from providers.base import BaseMockProvider


class GrokProvider(BaseMockProvider):
    provider_name = "grok"
    credential_env = "GROK_API_KEY"

