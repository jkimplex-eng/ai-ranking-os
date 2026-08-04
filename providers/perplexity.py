from providers.base import BaseMockProvider


class PerplexityProvider(BaseMockProvider):
    provider_name = "perplexity"
    credential_env = "PERPLEXITY_API_KEY"

