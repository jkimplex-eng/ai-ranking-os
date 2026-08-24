from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from competitor_intelligence.models import (
    CompetitorSocialPost,
    CompetitorSocialSource,
    TelegramConnection,
)
from competitor_intelligence.repository import CompetitorIntelligenceRepository
from competitor_intelligence.schemas import (
    TelegramCodeVerify,
    TelegramConnectionRead,
    TelegramConnectionStart,
    TelegramSearchRequest,
)
from competitor_intelligence.social_monitor import SocialMonitorError
from provider_connections.crypto import SecretCipher
from workspace.models import Project, ProjectCompetitor, UserWorkspace
from workspace.repository import CompetitorRepository, ProjectRepository, WorkspaceRepository


@dataclass(frozen=True)
class TelegramChallenge:
    session: str
    code_hash: str


@dataclass(frozen=True)
class TelegramMessage:
    channel_id: str
    channel_title: str
    channel_username: str | None
    message_id: int
    content: str
    published_at: datetime
    views: int | None
    forwards: int | None


class TelegramGatewayPort(Protocol):
    def send_code(
        self, api_id: int, api_hash: str, phone: str, proxy: dict | None
    ) -> TelegramChallenge: ...

    def verify(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        session: str,
        code_hash: str,
        code: str,
        password: str | None,
        proxy: dict | None,
    ) -> str: ...

    def search(
        self,
        api_id: int,
        api_hash: str,
        session: str,
        query: str,
        limit: int,
        proxy: dict | None,
    ) -> list[TelegramMessage]: ...


class TelethonGateway:
    @staticmethod
    def _run(awaitable):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, awaitable).result()

    @staticmethod
    def _proxy(value: dict | None):
        if not value:
            return None
        import socks

        return (
            socks.SOCKS5,
            value["host"],
            int(value["port"]),
            True,
            value.get("username"),
            value.get("password"),
        )

    @classmethod
    def _client(cls, session: str, api_id: int, api_hash: str, proxy: dict | None):
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        class DirectStringSession(StringSession):
            def set_dc(self, dc_id: int, server_address: str, port: int) -> None:
                super().set_dc(dc_id, server_address, 80)

        string_session = StringSession(session) if proxy else DirectStringSession(session)
        if not proxy and not string_session.server_address:
            string_session.set_dc(2, "149.154.167.51", 80)
        client = TelegramClient(
            string_session,
            api_id,
            api_hash,
            proxy=cls._proxy(proxy),
            connection_retries=2,
            timeout=15,
        )
        # Telegram supports MTProto on ports 80 and 443. Timeweb currently drops
        # outbound Telegram traffic on 443 while port 80 remains reachable. A
        # configured SOCKS proxy owns its destination routing and is left intact.
        return client

    def send_code(
        self, api_id: int, api_hash: str, phone: str, proxy: dict | None
    ) -> TelegramChallenge:
        async def run() -> TelegramChallenge:
            client = self._client("", api_id, api_hash, proxy)
            try:
                await client.connect()
                sent = await client.send_code_request(phone)
                return TelegramChallenge(client.session.save(), sent.phone_code_hash)
            finally:
                await client.disconnect()

        return self._run(run())

    def verify(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        session: str,
        code_hash: str,
        code: str,
        password: str | None,
        proxy: dict | None,
    ) -> str:
        async def run() -> str:
            from telethon.errors import SessionPasswordNeededError

            client = self._client(session, api_id, api_hash, proxy)
            try:
                await client.connect()
                try:
                    await client.sign_in(phone, code, phone_code_hash=code_hash)
                except SessionPasswordNeededError:
                    if not password:
                        raise SocialMonitorError("Для аккаунта требуется пароль 2FA") from None
                    await client.sign_in(password=password)
                if not await client.is_user_authorized():
                    raise SocialMonitorError("Telegram не подтвердил авторизацию")
                return client.session.save()
            finally:
                await client.disconnect()

        return self._run(run())

    def search(
        self,
        api_id: int,
        api_hash: str,
        session: str,
        query: str,
        limit: int,
        proxy: dict | None,
    ) -> list[TelegramMessage]:
        async def run() -> list[TelegramMessage]:
            from telethon.tl.functions.channels import SearchPostsRequest
            from telethon.tl.types import InputPeerEmpty

            client = self._client(session, api_id, api_hash, proxy)
            found: list[TelegramMessage] = []
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    raise SocialMonitorError("Telegram-сессия истекла; подключите аккаунт повторно")
                # This raw method searches Telegram's global index of public channel
                # posts, including channels which the account has not joined.
                result = await client(
                    SearchPostsRequest(
                        query=query,
                        offset_rate=0,
                        offset_peer=InputPeerEmpty(),
                        offset_id=0,
                        limit=min(limit, 100),
                    )
                )
                found.extend(self._messages(result))
                return found
            finally:
                await client.disconnect()

        return self._run(run())

    @staticmethod
    def _messages(result: object) -> list[TelegramMessage]:
        chats = {
            int(chat.id): chat
            for chat in getattr(result, "chats", [])
            if getattr(chat, "id", None) is not None
        }
        found: list[TelegramMessage] = []
        for message in getattr(result, "messages", []):
            content = getattr(message, "message", None)
            peer = getattr(message, "peer_id", None)
            channel_id = getattr(peer, "channel_id", None)
            if not content or channel_id is None:
                continue
            chat = chats.get(int(channel_id))
            username = getattr(chat, "username", None) if chat else None
            if not username:
                continue
            found.append(
                TelegramMessage(
                    channel_id=str(channel_id),
                    channel_title=getattr(chat, "title", username),
                    channel_username=username,
                    message_id=int(message.id),
                    content=content,
                    published_at=message.date,
                    views=getattr(message, "views", None),
                    forwards=getattr(message, "forwards", None),
                )
            )
        return found


class TelegramConnectionService:
    def __init__(self, db: Session, gateway: TelegramGatewayPort | None = None) -> None:
        self.db = db
        self.gateway = gateway or TelethonGateway()
        settings = get_settings()
        secret = settings.provider_secret_key or settings.auth_jwt_secret
        if len(secret) < 32:
            raise SocialMonitorError("На сервере не настроено шифрование Telegram-сессий")
        self.cipher = SecretCipher(secret)

    def status(self, user_id: int) -> TelegramConnectionRead:
        item = self._connection(user_id)
        if item is None:
            return TelegramConnectionRead(configured=False, status="NOT_CONFIGURED")
        return self._read(item)

    def start(self, user_id: int, payload: TelegramConnectionStart) -> TelegramConnectionRead:
        proxy = payload.proxy.model_dump(exclude_none=True) if payload.proxy else None
        try:
            challenge = self.gateway.send_code(
                payload.api_id, payload.api_hash, payload.phone_number, proxy
            )
        except Exception as error:
            raise SocialMonitorError(self._safe_error(error)) from error
        item = self._connection(user_id) or TelegramConnection(
            user_id=user_id,
            api_id=payload.api_id,
            encrypted_api_hash="",
            encrypted_phone="",
            phone_hint=self._phone_hint(payload.phone_number),
        )
        item.api_id = payload.api_id
        item.encrypted_api_hash = self.cipher.encrypt(payload.api_hash)
        item.encrypted_phone = self.cipher.encrypt(payload.phone_number)
        item.encrypted_session = self.cipher.encrypt(challenge.session)
        item.encrypted_code_hash = self.cipher.encrypt(challenge.code_hash)
        item.encrypted_proxy = self.cipher.encrypt(json.dumps(proxy)) if proxy else None
        item.phone_hint = self._phone_hint(payload.phone_number)
        item.status = "PENDING_CODE"
        item.last_error = None
        self.db.add(item)
        self.db.commit()
        return self._read(item)

    def verify(self, user_id: int, payload: TelegramCodeVerify) -> TelegramConnectionRead:
        item = self._required(user_id)
        if not item.encrypted_session or not item.encrypted_code_hash:
            raise SocialMonitorError("Сначала запросите код Telegram")
        try:
            session = self.gateway.verify(
                item.api_id,
                self.cipher.decrypt(item.encrypted_api_hash),
                self.cipher.decrypt(item.encrypted_phone),
                self.cipher.decrypt(item.encrypted_session),
                self.cipher.decrypt(item.encrypted_code_hash),
                payload.code,
                payload.password,
                self._proxy(item),
            )
        except Exception as error:
            item.last_error = self._safe_error(error)
            self.db.commit()
            raise SocialMonitorError(item.last_error) from error
        item.encrypted_session = self.cipher.encrypt(session)
        item.encrypted_code_hash = None
        item.status = "CONNECTED"
        item.last_error = None
        item.last_connected_at = datetime.now(UTC)
        item.next_search_at = datetime.now(UTC)
        self.db.commit()
        return self._read(item)

    def disconnect(self, user_id: int) -> None:
        item = self._connection(user_id)
        if item:
            self.db.delete(item)
            self.db.commit()

    def search_competitor(
        self,
        user_id: int,
        project_id: int,
        competitor_id: int,
        payload: TelegramSearchRequest,
    ) -> int:
        workspace = WorkspaceRepository(self.db).get_or_create(user_id)
        ProjectRepository(self.db).get(workspace.id, project_id)
        competitor = CompetitorRepository(self.db).get(project_id, competitor_id)
        item = self._required(user_id)
        if item.status != "CONNECTED" or not item.encrypted_session:
            raise SocialMonitorError("Сначала подключите Telegram")
        queries = [payload.query] if payload.query else [competitor.name, *competitor.brands]
        queries = list(dict.fromkeys(query.strip() for query in queries if query and query.strip()))
        messages: dict[tuple[str, int], TelegramMessage] = {}
        try:
            for query in queries[:10]:
                for message in self.gateway.search(
                    item.api_id,
                    self.cipher.decrypt(item.encrypted_api_hash),
                    self.cipher.decrypt(item.encrypted_session),
                    query,
                    payload.limit,
                    self._proxy(item),
                ):
                    messages[(message.channel_id, message.message_id)] = message
        except Exception as error:
            item.last_error = self._safe_error(error)
            self.db.commit()
            raise SocialMonitorError(item.last_error) from error
        repository = CompetitorIntelligenceRepository(self.db)
        sources = {
            source.external_id: source
            for source in repository.social_sources(competitor_id)
            if source.platform == "TELEGRAM"
        }
        now = datetime.now(UTC)
        for message in messages.values():
            source_key = message.channel_username or message.channel_id
            source = sources.get(source_key)
            if source is None:
                profile = (
                    f"https://t.me/{message.channel_username}"
                    if message.channel_username
                    else f"https://t.me/c/{message.channel_id}"
                )
                source = repository.add_social_source(
                    CompetitorSocialSource(
                        competitor_id=competitor_id,
                        platform="TELEGRAM",
                        profile_url=profile,
                        external_id=source_key,
                        active=bool(message.channel_username),
                        status="CONNECTED",
                        last_scanned_at=now,
                        next_scan_at=None,
                    )
                )
                sources[source_key] = source
            external_id = str(message.message_id)
            post = repository.social_post(source.id, external_id)
            if post is None:
                post = CompetitorSocialPost(
                    source_id=source.id,
                    external_post_id=external_id,
                    url=(
                        f"https://t.me/{message.channel_username}/{message.message_id}"
                        if message.channel_username
                        else source.profile_url
                    ),
                    published_at=message.published_at,
                )
                self.db.add(post)
            post.title = message.channel_title
            post.content = message.content
            post.views = message.views
            post.shares = message.forwards
            post.raw_metrics = {"matched_queries": queries, "source": "TELEGRAM_MTPROTO"}
            post.last_seen_at = now
        item.last_connected_at = now
        item.next_search_at = now + timedelta(days=1)
        item.last_error = None
        self.db.commit()
        return len(messages)

    def run_due(self) -> int:
        now = datetime.now(UTC)
        connections = list(
            self.db.scalars(
                select(TelegramConnection).where(
                    TelegramConnection.status == "CONNECTED",
                    (
                        TelegramConnection.next_search_at.is_(None)
                        | (TelegramConnection.next_search_at <= now)
                    ),
                )
            )
        )
        completed = 0
        for connection in connections:
            rows = list(
                self.db.execute(
                    select(Project.id, ProjectCompetitor.id)
                    .join(UserWorkspace, Project.workspace_id == UserWorkspace.id)
                    .join(ProjectCompetitor, ProjectCompetitor.project_id == Project.id)
                    .where(
                        UserWorkspace.user_id == connection.user_id,
                        ProjectCompetitor.active.is_(True),
                    )
                )
            )
            for project_id, competitor_id in rows:
                try:
                    self.search_competitor(
                        connection.user_id,
                        project_id,
                        competitor_id,
                        TelegramSearchRequest(limit=50),
                    )
                    completed += 1
                except SocialMonitorError:
                    continue
            connection.next_search_at = now + timedelta(days=1)
            self.db.commit()
        return completed

    def _connection(self, user_id: int) -> TelegramConnection | None:
        return self.db.scalar(
            select(TelegramConnection).where(TelegramConnection.user_id == user_id)
        )

    def _required(self, user_id: int) -> TelegramConnection:
        item = self._connection(user_id)
        if item is None:
            raise SocialMonitorError("Telegram ещё не подключён")
        return item

    def _proxy(self, item: TelegramConnection) -> dict | None:
        return (
            json.loads(self.cipher.decrypt(item.encrypted_proxy)) if item.encrypted_proxy else None
        )

    @staticmethod
    def _phone_hint(phone: str) -> str:
        return f"{phone[:3]}***{phone[-2:]}"

    @staticmethod
    def _safe_error(error: Exception) -> str:
        name = type(error).__name__
        safe = {
            "ApiIdInvalidError": "Telegram отклонил API ID или API Hash",
            "PhoneNumberInvalidError": "Telegram отклонил номер телефона",
            "PhoneCodeInvalidError": "Неверный код Telegram",
            "PhoneCodeExpiredError": "Код Telegram истёк; запросите новый",
            "PasswordHashInvalidError": "Неверный пароль 2FA",
            "FloodWaitError": "Telegram временно ограничил запросы; повторите позже",
            "ConnectionError": (
                "VPS не может установить соединение с Telegram; повторите через минуту"
            ),
            "PremiumAccountRequiredError": (
                "Глобальный поиск по публичным каналам требует Telegram Premium "
                "для подключённого аккаунта"
            ),
        }
        return safe.get(name, str(error)[:500] or "Ошибка соединения с Telegram")

    @staticmethod
    def _read(item: TelegramConnection) -> TelegramConnectionRead:
        return TelegramConnectionRead(
            configured=item.status == "CONNECTED",
            status=item.status,
            phone_hint=item.phone_hint,
            last_connected_at=item.last_connected_at,
            last_error=item.last_error,
        )
