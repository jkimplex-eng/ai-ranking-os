from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from backend.app.config import Settings
from provider_connections.crypto import SecretCipher
from yandex_webmaster.models import YandexWebmasterConnection, YandexWebmasterOAuthState
from yandex_webmaster.repository import YandexWebmasterRepository
from yandex_webmaster.schemas import ConnectionRead, HostRead, QueryRead


class YandexWebmasterError(ValueError):
    pass


class YandexWebmasterService:
    AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
    TOKEN_URL = "https://oauth.yandex.ru/token"
    API_URL = "https://api.webmaster.yandex.net/v4"

    def __init__(
        self,
        repository: YandexWebmasterRepository,
        cipher: SecretCipher,
        settings: Settings,
        client: httpx.Client | None = None,
    ) -> None:
        self.repository = repository
        self.cipher = cipher
        self.settings = settings
        self.client = client or httpx.Client(timeout=20)

    def _configured(self) -> tuple[str, str]:
        if not self.settings.yandex_webmaster_client_id:
            raise YandexWebmasterError("Интеграция Яндекс Вебмастера ещё не настроена на сервере")
        if not self.settings.yandex_webmaster_client_secret:
            raise YandexWebmasterError("OAuth Secret Яндекс Вебмастера отсутствует на сервере")
        return (
            self.settings.yandex_webmaster_client_id,
            self.settings.yandex_webmaster_client_secret,
        )

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def authorization_url(self, organization_id: int, user_id: int) -> str:
        client_id, _ = self._configured()
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        self.repository.save(
            YandexWebmasterOAuthState(
                state_hash=self._hash(state),
                organization_id=organization_id,
                user_id=user_id,
                verifier_ciphertext=self.cipher.encrypt(verifier),
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        parameters = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": self.settings.yandex_webmaster_redirect_uri,
            "scope": "webmaster:hostinfo",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "force_confirm": "yes",
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(parameters)}"

    def complete(self, code: str, state: str) -> YandexWebmasterConnection:
        client_id, client_secret = self._configured()
        oauth_state = self.repository.state(self._hash(state))
        now = datetime.now(UTC)
        expires_at = oauth_state.expires_at if oauth_state else None
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if not oauth_state or oauth_state.used_at or not expires_at or expires_at < now:
            raise YandexWebmasterError("OAuth-сессия недействительна или истекла")
        response = self.client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": self.settings.yandex_webmaster_redirect_uri,
                "code_verifier": self.cipher.decrypt(oauth_state.verifier_ciphertext),
            },
        )
        if response.status_code >= 400:
            raise YandexWebmasterError("Яндекс отклонил завершение OAuth-подключения")
        token = response.json()
        access_token = token.get("access_token")
        if not access_token:
            raise YandexWebmasterError("Яндекс не вернул access token")
        user_response = self.client.get(
            f"{self.API_URL}/user", headers={"Authorization": f"OAuth {access_token}"}
        )
        if user_response.status_code >= 400:
            raise YandexWebmasterError("Не удалось проверить доступ к Яндекс Вебмастеру")
        user_id = str(user_response.json().get("user_id", ""))
        if not user_id:
            raise YandexWebmasterError("Яндекс Вебмастер не вернул идентификатор пользователя")
        connection = self.repository.connection(oauth_state.organization_id)
        if connection is None:
            connection = YandexWebmasterConnection(
                organization_id=oauth_state.organization_id,
                yandex_user_id=user_id,
                access_token_ciphertext="",
                created_by=oauth_state.user_id,
            )
        connection.yandex_user_id = user_id
        connection.access_token_ciphertext = self.cipher.encrypt(access_token)
        refresh_token = token.get("refresh_token")
        if refresh_token:
            connection.refresh_token_ciphertext = self.cipher.encrypt(refresh_token)
        expires_in = token.get("expires_in")
        connection.expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None
        connection.status = "CONNECTED"
        connection.last_checked_at = now
        connection.last_success_at = now
        connection.last_error = None
        connection.updated_at = now
        oauth_state.used_at = now
        self.repository.save(oauth_state)
        return self.repository.save(connection)

    @staticmethod
    def read(connection: YandexWebmasterConnection | None) -> ConnectionRead:
        if not connection:
            return ConnectionRead(connected=False, status="NOT_CONFIGURED")
        return ConnectionRead(
            connected=connection.status == "CONNECTED",
            status=connection.status,
            selected_host_id=connection.selected_host_id,
            selected_host_url=connection.selected_host_url,
            last_checked_at=connection.last_checked_at,
            last_success_at=connection.last_success_at,
            last_error=connection.last_error,
        )

    def _connection(self, organization_id: int) -> tuple[YandexWebmasterConnection, str]:
        connection = self.repository.connection(organization_id)
        if not connection or connection.status != "CONNECTED":
            raise YandexWebmasterError("Сначала подключите Яндекс Вебмастер")
        return connection, self.cipher.decrypt(connection.access_token_ciphertext)

    def hosts(self, organization_id: int) -> list[HostRead]:
        connection, token = self._connection(organization_id)
        response = self.client.get(
            f"{self.API_URL}/user/{connection.yandex_user_id}/hosts",
            headers={"Authorization": f"OAuth {token}"},
        )
        if response.status_code >= 400:
            raise YandexWebmasterError("Не удалось получить сайты из Яндекс Вебмастера")
        return [
            HostRead(
                host_id=str(item.get("host_id", "")),
                ascii_host_url=item.get("ascii_host_url") or item.get("unicode_host_url") or "",
                unicode_host_url=item.get("unicode_host_url"),
                verified=str(item.get("verification", {}).get("verification_state", "")).upper()
                == "VERIFIED",
            )
            for item in response.json().get("hosts", [])
        ]

    def select_host(self, organization_id: int, host_id: str, host_url: str) -> ConnectionRead:
        connection, _ = self._connection(organization_id)
        connection.selected_host_id = host_id
        connection.selected_host_url = host_url
        connection.updated_at = datetime.now(UTC)
        return self.read(self.repository.save(connection))

    def popular_queries(self, organization_id: int, limit: int = 100) -> list[QueryRead]:
        connection, token = self._connection(organization_id)
        if not connection.selected_host_id:
            raise YandexWebmasterError("Выберите сайт Яндекс Вебмастера")
        response = self.client.get(
            f"{self.API_URL}/user/{connection.yandex_user_id}/hosts/{connection.selected_host_id}/search-queries/popular",
            params={"query_indicator": "TOTAL_SHOWS", "limit": min(limit, 500)},
            headers={"Authorization": f"OAuth {token}"},
        )
        if response.status_code >= 400:
            raise YandexWebmasterError("Не удалось получить поисковые запросы выбранного сайта")
        return [
            QueryRead(
                query_id=str(item.get("query_id")) if item.get("query_id") is not None else None,
                query_text=item.get("query_text", ""),
                indicators=item.get("indicators", {}),
            )
            for item in response.json().get("queries", [])
        ]

    def disconnect(self, organization_id: int) -> None:
        connection = self.repository.connection(organization_id)
        if connection:
            self.repository.delete(connection)
