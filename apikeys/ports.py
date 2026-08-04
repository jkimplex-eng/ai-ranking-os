from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ApiKeyPrincipal:
    key_id: int
    owner_id: int
    scopes: tuple[str, ...]
    rate_plan: str


class ApiKeyValidator(Protocol):
    def validate(self, credential: str, required_scope: str | None = None) -> ApiKeyPrincipal: ...
