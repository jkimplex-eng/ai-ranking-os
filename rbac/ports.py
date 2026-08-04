from typing import Protocol


class AuthorizationProvider(Protocol):
    def is_allowed(
        self, user_id: int, resource: str, action: str, scope: str = "global"
    ) -> bool: ...
