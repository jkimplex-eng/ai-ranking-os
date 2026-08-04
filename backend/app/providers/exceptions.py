from enum import StrEnum


class ProviderErrorCategory(StrEnum):
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    VALIDATION = "validation"
    INTERNAL = "provider_internal"
    PARSING = "parsing"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    CONFIGURATION = "configuration"


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        category: ProviderErrorCategory,
        provider: str,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code

