from providers.base import BaseMockProvider


class MistralProvider(BaseMockProvider):
    provider_name = "mistral"
    credential_env = "MISTRAL_API_KEY"

