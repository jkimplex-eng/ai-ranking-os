from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

import httpx

from backend.app.providers.credentials import credentials
from provider_connections.crypto import SecretCipher
from provider_connections.models import ProviderConnection
from provider_connections.repository import ProviderConnectionRepository
from provider_connections.schemas import ConnectionCreate, ConnectionRead, ConnectionTestRead


class ProviderConnectionError(ValueError):
    pass


PROVIDERS = {
    "openrouter": {
        "display_name": "OpenRouter",
        "credential": "OPENROUTER_API_KEY",
        "models_url": "https://openrouter.ai/api/v1/models",
    },
    "groq": {
        "display_name": "Groq",
        "credential": "GROQ_API_KEY",
        "models_url": "https://api.groq.com/openai/v1/models",
    },
    "github": {
        "display_name": "GitHub Models",
        "credential": "GITHUB_MODELS_TOKEN",
        "models_url": "https://models.github.ai/catalog/models",
    },
    "huggingface": {
        "display_name": "Hugging Face",
        "credential": "HUGGINGFACE_API_KEY",
        "models_url": "https://huggingface.co/api/models?inference_provider=all&limit=10",
    },
    "cerebras": {
        "display_name": "Cerebras",
        "credential": "CEREBRAS_API_KEY",
        "models_url": "https://api.cerebras.ai/v1/models",
    },
    "mistral": {
        "display_name": "Mistral",
        "credential": "MISTRAL_API_KEY",
        "models_url": "https://api.mistral.ai/v1/models",
    },
    "yandex": {
        "display_name": "YandexGPT",
        "credential": "YANDEX_API_KEY",
        "project_credential": "YANDEX_FOLDER_ID",
        "models_url": "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
    },
}


class ProviderDetector:
    PREFIXES = (
        ("sk-or-v1-", "openrouter"),
        ("gsk_", "groq"),
        ("github_pat_", "github"),
        ("ghp_", "github"),
        ("hf_", "huggingface"),
        ("csk-", "cerebras"),
    )

    @classmethod
    def detect(cls, key: str, hint: str | None = None) -> str:
        normalized_hint = (hint or "").casefold().strip()
        if normalized_hint:
            if normalized_hint not in PROVIDERS:
                raise ProviderConnectionError("Этот провайдер пока не поддерживается")
            return normalized_hint
        for prefix, provider in cls.PREFIXES:
            if key.startswith(prefix):
                return provider
        raise ProviderConnectionError(
            "Формат ключа неоднозначен. Выберите провайдера — "
            "ключ не будет отправлен другим компаниям."
        )


class ProviderConnectionService:
    def __init__(self, repository: ProviderConnectionRepository, cipher: SecretCipher) -> None:
        self.repository = repository
        self.cipher = cipher

    @staticmethod
    def _read(item: ProviderConnection) -> ConnectionRead:
        return ConnectionRead(
            id=item.id,
            organization_id=item.organization_id,
            provider=item.provider,
            display_name=item.display_name,
            masked_key=f"••••••••{item.secret_suffix}",
            status=item.status,
            free_only=item.free_only,
            paid_fallback=item.paid_fallback,
            last_checked_at=item.last_checked_at,
            last_success_at=item.last_success_at,
            last_error=item.last_error,
            created_at=item.created_at,
        )

    def list(self, organization_id: int) -> list[ConnectionRead]:
        return [self._read(item) for item in self.repository.list(organization_id)]

    def create(
        self, organization_id: int, user_id: int, payload: ConnectionCreate
    ) -> ConnectionRead:
        provider = ProviderDetector.detect(payload.api_key.strip(), payload.provider_hint)
        definition = PROVIDERS[provider]
        if provider == "yandex" and not payload.folder_id:
            raise ProviderConnectionError("Для YandexGPT укажите Folder ID каталога")
        existing = self.repository.by_provider(organization_id, provider)
        if existing:
            existing.secret_ciphertext = self.cipher.encrypt(payload.api_key.strip())
            existing.secret_suffix = payload.api_key.strip()[-4:]
            existing.project_ciphertext = (
                self.cipher.encrypt(payload.folder_id.strip()) if payload.folder_id else None
            )
            existing.status = "PENDING_CHECK"
            existing.free_only = payload.free_only
            existing.paid_fallback = False
            existing.updated_at = datetime.now(UTC)
            item = self.repository.save(existing)
        else:
            item = self.repository.save(
                ProviderConnection(
                    organization_id=organization_id,
                    provider=provider,
                    display_name=definition["display_name"],
                    credential_name=definition["credential"],
                    secret_ciphertext=self.cipher.encrypt(payload.api_key.strip()),
                    secret_suffix=payload.api_key.strip()[-4:],
                    project_ciphertext=(
                        self.cipher.encrypt(payload.folder_id.strip())
                        if payload.folder_id
                        else None
                    ),
                    status="PENDING_CHECK",
                    free_only=payload.free_only,
                    paid_fallback=False,
                    created_by=user_id,
                )
            )
        self.test(item.id, organization_id)
        self.repository.audit(organization_id, user_id, "provider_connection.created", item.id)
        return self._read(item)

    def test(self, connection_id: int, organization_id: int) -> ConnectionTestRead:
        item = self._owned(connection_id, organization_id)
        key = self.cipher.decrypt(item.secret_ciphertext)
        started = perf_counter()
        checked_at = datetime.now(UTC)
        models: list[str] = []
        try:
            if item.provider == "yandex":
                folder = self._project_value(item)
                response = httpx.post(
                    PROVIDERS[item.provider]["models_url"],
                    headers={
                        "Authorization": f"Api-Key {key}",
                        "x-folder-id": folder,
                        "Content-Type": "application/json",
                    },
                    json={
                        "modelUri": f"gpt://{folder}/yandexgpt-lite/latest",
                        "completionOptions": {
                            "stream": False,
                            "temperature": 0,
                            "maxTokens": "1",
                        },
                        "messages": [{"role": "user", "text": "ping"}],
                    },
                    timeout=20,
                )
            else:
                response = httpx.get(
                    PROVIDERS[item.provider]["models_url"],
                    headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                    timeout=15,
                )
            response.raise_for_status()
            body = response.json()
            if item.provider == "yandex":
                models = ["yandexgpt-lite", "yandexgpt-pro"]
            else:
                values = body.get("data", body) if isinstance(body, dict) else body
                models = [
                    str(value.get("id") or value.get("name"))
                    for value in values[:200]
                    if isinstance(value, dict) and (value.get("id") or value.get("name"))
                ]
            item.status = "CONNECTED"
            item.last_success_at = checked_at
            item.last_error = None
            credentials.set(item.credential_name, key)
            if item.provider == "yandex":
                credentials.set("YANDEX_FOLDER_ID", self._project_value(item))
        except (httpx.HTTPError, ValueError) as error:
            item.status = "UNAVAILABLE"
            item.last_checked_at = checked_at
            item.last_error = self._safe_error(error)
            self.repository.save(item)
            raise ProviderConnectionError(item.last_error) from error
        item.last_checked_at = checked_at
        self.repository.save(item)
        free_models = [model for model in models if model.endswith(":free")]
        if item.provider == "openrouter" and "openrouter/free" not in free_models:
            free_models.insert(0, "openrouter/free")
        return ConnectionTestRead(
            provider=item.provider,
            status=item.status,
            latency_ms=round((perf_counter() - started) * 1000),
            models=models,
            free_models=free_models,
            checked_at=checked_at,
        )

    def delete(self, connection_id: int, organization_id: int, user_id: int) -> None:
        item = self._owned(connection_id, organization_id)
        credentials.clear(item.credential_name)
        if item.provider == "yandex":
            credentials.clear("YANDEX_FOLDER_ID")
        self.repository.delete(item)
        self.repository.audit(
            organization_id, user_id, "provider_connection.revoked", connection_id
        )

    def _owned(self, connection_id: int, organization_id: int) -> ProviderConnection:
        item = self.repository.get(connection_id)
        if item is None or item.organization_id != organization_id:
            raise ProviderConnectionError("Подключение не найдено")
        return item

    def _project_value(self, item: ProviderConnection) -> str:
        if not item.project_ciphertext:
            raise ProviderConnectionError("Для YandexGPT не сохранён Folder ID")
        return self.cipher.decrypt(item.project_ciphertext)

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            messages = {
                401: "Ключ недействителен или отозван",
                402: "Недостаточно средств на аккаунте провайдера",
                403: "Доступ запрещён: проверьте права ключа, Folder ID или регион сервера",
                429: "Превышен лимит запросов провайдера",
            }
            return messages.get(
                error.response.status_code,
                f"Провайдер вернул HTTP {error.response.status_code}",
            )
        if isinstance(error, httpx.TimeoutException):
            return "Провайдер не ответил за 15 секунд"
        return "Не удалось проверить подключение к провайдеру"
