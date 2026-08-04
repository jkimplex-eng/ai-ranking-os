from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe

from apikeys.models import ApiKey
from apikeys.ports import ApiKeyPrincipal
from apikeys.repository import ApiKeyRepository
from apikeys.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyRead


class ApiKeyError(ValueError):
    pass


class ApiKeyNotFound(LookupError):
    pass


class ApiKeyService:
    def __init__(self, repository: ApiKeyRepository):
        self.repository = repository

    def create(self, data: ApiKeyCreate, rotated_from_id: int | None = None) -> ApiKeyCreated:
        prefix = f"ark_{token_urlsafe(6).replace('-', '')[:8]}"
        secret_part = token_urlsafe(32)
        secret = f"{prefix}.{secret_part}"
        key = self.repository.save(
            ApiKey(
                **data.model_dump(),
                prefix=prefix,
                secret_digest=sha256(secret.encode()).hexdigest(),
                rotated_from_id=rotated_from_id,
            )
        )
        return ApiKeyCreated(**ApiKeyRead.model_validate(key).model_dump(), secret=secret)

    def get(self, key_id: int) -> ApiKeyRead:
        return ApiKeyRead.model_validate(self._get(key_id))

    def list(self, owner_id: int | None = None) -> list[ApiKeyRead]:
        return [ApiKeyRead.model_validate(k) for k in self.repository.list(owner_id)]

    def revoke(self, key_id: int) -> ApiKeyRead:
        key = self._get(key_id)
        key.revoked_at = datetime.now(UTC)
        return ApiKeyRead.model_validate(self.repository.save(key))

    def rotate(self, key_id: int) -> ApiKeyCreated:
        old = self._get(key_id)
        if old.revoked_at:
            raise ApiKeyError("API key is revoked")
        created = self.create(
            ApiKeyCreate(
                name=old.name,
                owner_id=old.owner_id,
                scopes=old.scopes,
                rate_plan=old.rate_plan,
                expires_at=old.expires_at,
            ),
            old.id,
        )
        self.revoke(old.id)
        return created

    def validate(self, credential: str, required_scope: str | None = None) -> ApiKeyPrincipal:
        try:
            prefix, _ = credential.split(".", 1)
        except ValueError as error:
            raise ApiKeyError("Invalid API key") from error
        key = self.repository.by_prefix(prefix)
        now = datetime.now(UTC)
        if (
            not key
            or key.revoked_at
            or (key.expires_at and self._utc(key.expires_at) <= now)
            or not compare_digest(key.secret_digest, sha256(credential.encode()).hexdigest())
        ):
            raise ApiKeyError("Invalid API key")
        if required_scope and required_scope not in key.scopes and "*" not in key.scopes:
            raise ApiKeyError("Missing required scope")
        return ApiKeyPrincipal(key.id, key.owner_id, tuple(key.scopes), key.rate_plan)

    def _get(self, key_id: int) -> ApiKey:
        key = self.repository.get(key_id)
        if not key:
            raise ApiKeyNotFound("API key not found")
        return key

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
