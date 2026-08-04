import os
from collections.abc import Callable
from pathlib import Path
from threading import RLock

from backend.app.providers.exceptions import (
    ProviderError,
    ProviderErrorCategory,
)

VaultResolver = Callable[[str], str | None]


class CredentialManager:
    """Hot-reading credentials from ENV, mounted secrets, or a Vault resolver."""

    def __init__(
        self,
        *,
        docker_secrets_dir: Path = Path("/run/secrets"),
        kubernetes_secrets_dir: Path = Path("/var/run/secrets/ai-ranking-os"),
        vault_resolver: VaultResolver | None = None,
    ) -> None:
        self._directories = (docker_secrets_dir, kubernetes_secrets_dir)
        self._vault_resolver = vault_resolver
        self._overrides: dict[str, str] = {}
        self._lock = RLock()

    def set(self, name: str, value: str) -> None:
        with self._lock:
            self._overrides[name] = value

    def clear(self, name: str) -> None:
        with self._lock:
            self._overrides.pop(name, None)

    def get(self, name: str, *, required: bool = True) -> str | None:
        with self._lock:
            if name in self._overrides:
                return self._overrides[name]
        if value := os.getenv(name):
            return value
        for directory in self._directories:
            path = directory / name
            if path.is_file():
                value = path.read_text(encoding="utf-8").strip()
                if value:
                    return value
        if self._vault_resolver and (value := self._vault_resolver(name)):
            return value
        if required:
            raise ProviderError(
                f"Credential {name} is not configured",
                category=ProviderErrorCategory.CONFIGURATION,
                provider="credential-manager",
            )
        return None


credentials = CredentialManager()

