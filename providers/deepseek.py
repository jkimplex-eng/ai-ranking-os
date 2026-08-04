from providers.base import BaseMockProvider


class DeepSeekProvider(BaseMockProvider):
    provider_name = "deepseek"
    credential_env = "DEEPSEEK_API_KEY"

