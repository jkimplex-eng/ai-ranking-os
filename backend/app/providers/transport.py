from collections.abc import Iterator
from time import sleep
from typing import Any

import httpx

from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory


class HTTPTransport:
    def __init__(
        self,
        timeout_seconds: float = 30,
        max_retries: int = 3,
        retry_base_seconds: float = 0.25,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_base_seconds = max(0, retry_base_seconds)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            cause: Exception
            try:
                response = httpx.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as error:
                cause = error
                failure = ProviderError(
                    "Provider request timed out",
                    category=ProviderErrorCategory.TIMEOUT,
                    provider=url,
                    retryable=True,
                )
            except httpx.HTTPStatusError as error:
                cause = error
                status = error.response.status_code
                category = (
                    ProviderErrorCategory.AUTHENTICATION
                    if status in {401, 403}
                    else ProviderErrorCategory.RATE_LIMIT
                    if status == 429
                    else ProviderErrorCategory.INTERNAL
                )
                failure = ProviderError(
                    f"Provider returned HTTP {status}",
                    category=category,
                    provider=url,
                    retryable=status == 429 or status >= 500,
                    status_code=status,
                )
            except httpx.RequestError as error:
                cause = error
                failure = ProviderError(
                    "Provider network request failed",
                    category=ProviderErrorCategory.NETWORK,
                    provider=url,
                    retryable=True,
                )
            except ValueError as error:
                raise ProviderError(
                    "Provider response is not valid JSON",
                    category=ProviderErrorCategory.PARSING,
                    provider=url,
                ) from error
            if not failure.retryable or attempt >= self.max_retries:
                raise failure from cause
            sleep(self.retry_base_seconds * (2**attempt))
        raise RuntimeError("Provider retry loop exited unexpectedly")

    def stream(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> Iterator[str]:
        try:
            with httpx.stream(
                method,
                url,
                headers=headers,
                json=json,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                yield from response.iter_lines()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            category = (
                ProviderErrorCategory.AUTHENTICATION
                if status in {401, 403}
                else ProviderErrorCategory.RATE_LIMIT
                if status == 429
                else ProviderErrorCategory.INTERNAL
            )
            raise ProviderError(
                f"Provider stream returned HTTP {status}",
                category=category,
                provider=url,
                retryable=status == 429 or status >= 500,
                status_code=status,
            ) from error
        except httpx.TimeoutException as error:
            raise ProviderError(
                "Provider stream timed out",
                category=ProviderErrorCategory.TIMEOUT,
                provider=url,
                retryable=True,
            ) from error
        except httpx.RequestError as error:
            raise ProviderError(
                "Provider stream failed",
                category=ProviderErrorCategory.NETWORK,
                provider=url,
                retryable=True,
            ) from error
