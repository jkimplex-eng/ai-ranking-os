from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: int
    email: str
    session_id: str
    token_version: int


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, encoded: str, password: str) -> bool: ...


class TokenCodec(Protocol):
    def encode(self, claims: dict[str, object]) -> str: ...
    def decode(self, token: str, expected_type: str) -> dict[str, object]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdentityProvider(Protocol):
    """Extension port reserved for OAuth2/OpenID Connect providers."""

    def exchange(self, authorization_code: str) -> dict[str, str]: ...
