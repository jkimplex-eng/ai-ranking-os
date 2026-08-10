from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class BetaUserFacts:
    user_id: int
    email: str
    display_name: str
    is_active: bool
    registered_at: datetime
    last_seen_at: datetime | None


class IdentityPort(Protocol):
    def users(self) -> list[BetaUserFacts]: ...
    def exists(self, email: str) -> bool: ...
    def create(self, email: str, password: str, display_name: str) -> int: ...


class UsagePort(Protocol):
    def research_counts(self, user_ids: list[int]) -> dict[int, int]: ...


class RolePort(Protocol):
    def assign(self, user_id: int, role_id: int) -> None: ...
    def is_admin(self, user_id: int) -> bool: ...
