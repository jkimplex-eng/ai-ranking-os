from providers.base import BaseMockProvider


class LocalProvider(BaseMockProvider):
    provider_name = "local"
    credential_env = "LOCAL_MODEL_PATH"

