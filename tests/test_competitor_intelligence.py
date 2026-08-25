from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from competitor_intelligence.models import TelegramConnection
from competitor_intelligence.schemas import (
    SocialPlatform,
    SocialSourceCreate,
    TelegramCodeVerify,
    TelegramConnectionStart,
    TelegramProxyInput,
    TelegramSearchRequest,
)
from competitor_intelligence.social_monitor import (
    CollectedPost,
    CompetitorSocialMonitorService,
    DiscoveredSource,
    HttpSocialCollector,
    WebsiteSocialDiscovery,
)
from competitor_intelligence.telegram_connector import (
    TelegramChallenge,
    TelegramConnectionService,
    TelegramMessage,
    TelethonGateway,
)
from research.models import (
    ExtractedCitation,
    ExtractedEntity,
    ExtractedRecommendation,
    Research,
    ResearchStatus,
    ResearchTask,
    ResearchTaskStatus,
    Response,
    ResponseProcessingStatus,
)

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def test_telegram_global_search_maps_only_public_channel_posts() -> None:
    published = datetime(2026, 8, 24, tzinfo=UTC)
    result = SimpleNamespace(
        chats=[
            SimpleNamespace(id=100, title="Public Beauty", username="public_beauty"),
            SimpleNamespace(id=200, title="Private Beauty", username=None),
        ],
        messages=[
            SimpleNamespace(
                id=10,
                peer_id=SimpleNamespace(channel_id=100),
                message="Skinjestique serum",
                date=published,
                views=500,
                forwards=5,
            ),
            SimpleNamespace(
                id=20,
                peer_id=SimpleNamespace(channel_id=200),
                message="Not publicly addressable",
                date=published,
                views=None,
                forwards=None,
            ),
        ],
    )

    messages = TelethonGateway._messages(result)

    assert len(messages) == 1
    assert messages[0].channel_username == "public_beauty"
    assert messages[0].content == "Skinjestique serum"


def test_telegram_direct_connection_uses_reachable_mtproto_port() -> None:
    client = TelethonGateway._client("", 12345, "a" * 32, None)

    assert client.session.port == 80


def test_telegram_existing_session_is_moved_from_blocked_port() -> None:
    from telethon.sessions import StringSession

    stored = StringSession()
    stored.set_dc(2, "149.154.167.51", 443)

    client = TelethonGateway._client(stored.save(), 12345, "a" * 32, None)

    assert client.session.server_address == "149.154.167.51"
    assert client.session.port == 80


def test_telegram_proxy_preflight_checks_stored_dc_on_port_80(monkeypatch) -> None:
    from telethon.sessions import StringSession

    stored = StringSession()
    stored.set_dc(2, "149.154.167.51", 443)
    calls: dict[str, object] = {}

    class FakeSocket:
        def set_proxy(self, *args) -> None:
            calls["proxy"] = args

        def settimeout(self, timeout: int) -> None:
            calls["timeout"] = timeout

        def connect(self, target) -> None:
            calls["target"] = target

        def close(self) -> None:
            calls["closed"] = True

    monkeypatch.setattr("socks.socksocket", FakeSocket)

    TelethonGateway._check_proxy_route(
        stored.save(),
        {
            "protocol": "SOCKS5",
            "host": "proxy.example.com",
            "port": 1080,
            "username": "user",
            "password": "secret",
        },
    )

    assert calls["target"] == ("149.154.167.51", 443)
    assert calls["timeout"] == 12
    assert calls["closed"] is True


def test_telegram_proxy_preflight_reports_dns_error(monkeypatch) -> None:
    import socket

    from competitor_intelligence.social_monitor import SocialMonitorError

    class FakeSocket:
        def set_proxy(self, *args) -> None:
            pass

        def settimeout(self, timeout: int) -> None:
            pass

        def connect(self, target) -> None:
            raise socket.gaierror("not found")

        def close(self) -> None:
            pass

    monkeypatch.setattr("socks.socksocket", FakeSocket)

    with pytest.raises(SocialMonitorError, match="Адрес SOCKS5 не найден"):
        TelethonGateway._check_proxy_route(
            "",
            {"host": "missing.example.com", "port": 1080},
        )


def test_telegram_http_proxy_uses_http_connect() -> None:
    import socks

    proxy = TelethonGateway._proxy(
        {
            "protocol": "HTTP",
            "host": "p.webshare.io",
            "port": 80,
            "username": "user",
            "password": "secret",
        }
    )

    assert proxy == (socks.HTTP, "p.webshare.io", 80, True, "user", "secret")


def test_telegram_proxy_client_uses_standard_mtproto_port() -> None:
    from telethon.sessions import StringSession

    stored = StringSession()
    stored.set_dc(2, "149.154.167.51", 80)

    client = TelethonGateway._client(
        stored.save(),
        12345,
        "a" * 32,
        {"protocol": "HTTP", "host": "p.webshare.io", "port": 80},
    )

    assert client.session.port == 443


def test_telegram_mtproxy_uses_native_telethon_transport() -> None:
    from telethon.network.connection import ConnectionTcpMTProxyRandomizedIntermediate
    from telethon.sessions import StringSession

    stored = StringSession()
    stored.set_dc(2, "149.154.167.51", 80)
    proxy = {
        "protocol": "MTPROXY",
        "host": "proxy.example.com",
        "port": 443,
        "secret": "dd" + "a" * 32,
    }

    client = TelethonGateway._client(stored.save(), 12345, "a" * 32, proxy)

    assert TelethonGateway._proxy(proxy) == (
        "proxy.example.com",
        443,
        "dd" + "a" * 32,
    )
    assert client._connection is ConnectionTcpMTProxyRandomizedIntermediate
    assert client.session.port == 443


def test_telegram_faketls_mtproxy_uses_tgnet_transport() -> None:
    from telethon.sessions import StringSession
    from tgnet.connection.faketls import TgNetConnectionTls

    stored = StringSession()
    stored.set_dc(2, "149.154.167.51", 80)
    proxy = {
        "protocol": "MTPROXY",
        "host": "proxy.example.com",
        "port": 8443,
        "secret": "7iVzxL2VgpVP1pd962HLwKtwZXRyb3ZpY2gucnU",
    }

    client = TelethonGateway._client(stored.save(), 12345, "a" * 32, proxy)

    assert issubclass(client._connection, TgNetConnectionTls)
    assert TelethonGateway._mtproxy_secret(proxy["secret"]).hex() == (
        "ee2573c4bd9582954fd6977deb61cbc0ab706574726f766963682e7275"
    )


def test_telegram_mtproxy_requires_secret() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Для MTProxy требуется secret"):
        TelegramProxyInput(
            protocol="MTPROXY",
            host="proxy.example.com",
            port=443,
        )


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _project_and_competitor(client: TestClient) -> tuple[int, int]:
    project = client.post("/workspace/projects", json={"name": "Skinjestique"})
    project_id = project.json()["id"]
    competitor = client.post(
        f"/workspace/projects/{project_id}/competitors",
        json={
            "name": "Librederm",
            "domains": ["librederm.ru"],
            "brands": ["Либридерм"],
        },
    )
    return project_id, competitor.json()["id"]


class _TelegramGateway:
    checked_proxy = None

    def send_code(self, api_id, api_hash, phone, proxy):
        assert api_id == 12345
        assert api_hash == "a" * 32
        assert phone == "+79991234567"
        return TelegramChallenge("pending-session", "code-hash")

    def verify(self, api_id, api_hash, phone, session, code_hash, code, password, proxy):
        assert session == "pending-session"
        assert code_hash == "code-hash"
        assert code == "12345"
        return "authorized-session"

    def search(self, api_id, api_hash, session, query, limit, proxy):
        assert session == "authorized-session"
        return [
            TelegramMessage(
                channel_id="777",
                channel_title="Beauty News",
                channel_username="beauty_news",
                message_id=42,
                content=f"Публикация про {query}",
                published_at=datetime(2026, 8, 24, tzinfo=UTC),
                views=1500,
                forwards=12,
            )
        ]

    def check(self, api_id, api_hash, session, proxy):
        assert session == "authorized-session"
        self.checked_proxy = proxy


def _completed_research(project_id: int) -> int:
    finished_at = datetime(2026, 8, 20, 9, 30, tzinfo=UTC)
    with TestingSession() as db:
        research = Research(
            project_id=project_id,
            title="Конкурентное исследование",
            objective="Какую увлажняющую сыворотку выбрать?",
            status=ResearchStatus.COMPLETED,
            total_tasks=1,
            completed_tasks=1,
            progress_percent=100,
            created_at=finished_at,
            updated_at=finished_at,
        )
        task = ResearchTask(
            query="Какую увлажняющую сыворотку выбрать?",
            status=ResearchTaskStatus.COMPLETED,
            provider="yandex",
            model="yandexgpt-pro",
        )
        response = Response(
            provider="yandex",
            model="yandexgpt-pro",
            prompt=task.query,
            content="Рекомендую Librederm. Источник — отраслевой обзор.",
            processing_status=ResponseProcessingStatus.PROCESSED,
            finished_at=finished_at,
        )
        response.extracted_entities.append(
            ExtractedEntity(
                name="Librederm",
                canonical_name="Librederm",
                entity_type="BRAND",
                confidence=0.96,
            )
        )
        response.extracted_recommendations.append(
            ExtractedRecommendation(
                content="Рекомендую Librederm для увлажнения",
                rank=1,
                confidence=0.92,
            )
        )
        response.extracted_citations.append(
            ExtractedCitation(
                url="https://beauty.example/reviews/serums",
                title="Обзор увлажняющих сывороток",
                source="beauty.example",
                excerpt="Librederm вошёл в подборку",
                position=1,
            )
        )
        task.responses.append(response)
        research.tasks.append(task)
        db.add(research)
        db.commit()
        return research.id


def test_refresh_builds_visibility_and_publication_evidence(client: TestClient) -> None:
    project_id, competitor_id = _project_and_competitor(client)
    _completed_research(project_id)

    refreshed = client.post(f"/competitor-intelligence/projects/{project_id}/refresh")

    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["methodology"] == "COMPETITOR_OBSERVATION_V1"
    assert "не доказывает причинное" in body["limitation"]
    analytics = body["competitors"][0]
    assert analytics["competitor_id"] == competitor_id
    assert analytics["latest_visibility_score"] == 100
    assert analytics["snapshots"][0]["mention_count"] == 1
    assert analytics["snapshots"][0]["recommendation_count"] == 1
    publication = analytics["publications"][0]
    assert publication["domain"] == "beauty.example"
    assert publication["research_count"] == 1
    assert publication["evidence_level"] == "OBSERVATION"
    assert "ответах" in publication["explanation"]


def test_daily_monitoring_reuses_completed_research_template(client: TestClient) -> None:
    project_id, _ = _project_and_competitor(client)
    _completed_research(project_id)

    enabled = client.put(
        f"/competitor-intelligence/projects/{project_id}/daily-monitoring",
        json={"enabled": True},
    )

    assert enabled.status_code == 200
    assert enabled.json()["monitoring_enabled"] is True
    assert enabled.json()["next_run_at"] is not None
    disabled = client.put(
        f"/competitor-intelligence/projects/{project_id}/daily-monitoring",
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["monitoring_enabled"] is False


def test_competitor_intelligence_is_documented_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/competitor-intelligence/projects/{project_id}" in paths
    assert "/competitor-intelligence/projects/{project_id}/refresh" in paths
    assert "/competitor-intelligence/projects/{project_id}/daily-monitoring" in paths
    assert (
        "/competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/social" in paths
    )
    assert (
        "/competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/social/discover"
        in paths
    )
    assert "/competitor-intelligence/telegram/connection/send-code" in paths
    assert "/competitor-intelligence/telegram/connection/verify" in paths
    assert (
        "/competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/telegram/search"
        in paths
    )


class _SocialCollector:
    def collect(self, source, token):  # noqa: ANN001, ANN201
        assert source.external_id == "skinjestique"
        assert token is None
        return [
            CollectedPost(
                external_id="skinjestique/42",
                url="https://t.me/skinjestique/42",
                title="Новая сыворотка",
                content="Разбор увлажняющей сыворотки",
                published_at=datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
            )
        ]


class _SocialDiscovery:
    def discover(self, domains):  # noqa: ANN001, ANN201
        assert domains
        return [
            DiscoveredSource(
                platform=SocialPlatform.TELEGRAM,
                profile_url="https://t.me/skinjestique",
                external_id="skinjestique",
            )
        ]


def test_website_discovery_extracts_only_explicit_social_profiles(monkeypatch) -> None:
    markup = """
    <a href="https://t.me/skinjestique">Telegram</a>
    <a href="https://www.youtube.com/@skinjestique">YouTube</a>
    <a href="https://instagram.com/skinjestique/">Instagram</a>
    <a href="https://t.me/share/url?url=example.org">Share</a>
    """
    monkeypatch.setattr(
        "competitor_intelligence.social_monitor.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        HttpSocialCollector,
        "_get",
        staticmethod(
            lambda url, params=None: httpx.Response(
                200,
                text=markup,
                request=httpx.Request("GET", url),
            )
        ),
    )

    sources = WebsiteSocialDiscovery().discover(["example.com"])

    assert {(item.platform, item.external_id) for item in sources} == {
        (SocialPlatform.TELEGRAM, "skinjestique"),
        (SocialPlatform.YOUTUBE, "skinjestique"),
        (SocialPlatform.INSTAGRAM, "skinjestique"),
    }


def test_social_monitor_discovers_and_deduplicates_official_profiles(
    client: TestClient,
) -> None:
    project_id, competitor_id = _project_and_competitor(client)
    with TestingSession() as db:
        service = CompetitorSocialMonitorService(db, _SocialCollector(), _SocialDiscovery())
        first = service.discover(1, project_id, competitor_id)
        second = service.discover(1, project_id, competitor_id)

    assert first.total_posts == 1
    assert len(first.sources) == 1
    assert len(second.sources) == 1
    assert first.sources[0].status == "CONNECTED"


def test_social_monitor_saves_real_collector_results(client: TestClient) -> None:
    project_id, competitor_id = _project_and_competitor(client)
    with TestingSession() as db:
        source = CompetitorSocialMonitorService(db, _SocialCollector()).create(
            1,
            project_id,
            competitor_id,
            SocialSourceCreate(
                platform="TELEGRAM",
                profile_url="https://t.me/skinjestique",
                external_id="skinjestique",
            ),
        )

    assert source.status == "CONNECTED"
    assert source.configured is True
    assert len(source.posts) == 1
    assert source.posts[0].url == "https://t.me/skinjestique/42"
    assert source.posts[0].significance_score == 0

    dashboard = client.get(
        f"/competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/social"
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["total_posts"] == 1
    assert "не доказывает влияние" in dashboard.json()["limitation"]


def test_telegram_connection_encrypts_credentials_and_searches_message_content(
    client: TestClient, monkeypatch
) -> None:
    project_id, competitor_id = _project_and_competitor(client)
    settings = type(
        "Settings",
        (),
        {"provider_secret_key": "t" * 32, "auth_jwt_secret": "j" * 32},
    )()
    monkeypatch.setattr("competitor_intelligence.telegram_connector.get_settings", lambda: settings)
    with TestingSession() as db:
        service = TelegramConnectionService(db, _TelegramGateway())
        pending = service.start(
            1,
            TelegramConnectionStart(
                api_id=12345,
                api_hash="a" * 32,
                phone_number="+79991234567",
            ),
        )
        assert pending.status == "PENDING_CODE"
        connected = service.verify(1, TelegramCodeVerify(code="12345"))
        assert connected.configured is True
        count = service.search_competitor(
            1, project_id, competitor_id, TelegramSearchRequest(limit=20)
        )
        stored = service.db.scalar(
            select(TelegramConnection).where(TelegramConnection.user_id == 1)
        )

    assert count == 1
    assert stored is not None
    assert "aaaaaaaa" not in stored.encrypted_api_hash
    assert "+7999" not in stored.encrypted_phone
    dashboard = client.get(
        f"/competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/social"
    ).json()
    assert dashboard["total_posts"] == 1
    assert all("Публикация про" in post["content"] for post in dashboard["sources"][0]["posts"])


def test_telegram_proxy_is_checked_and_encrypted(client: TestClient, monkeypatch) -> None:
    _project_and_competitor(client)
    settings = type(
        "Settings",
        (),
        {"provider_secret_key": "t" * 32, "auth_jwt_secret": "j" * 32},
    )()
    monkeypatch.setattr("competitor_intelligence.telegram_connector.get_settings", lambda: settings)
    gateway = _TelegramGateway()
    with TestingSession() as db:
        service = TelegramConnectionService(db, gateway)
        service.start(
            1,
            TelegramConnectionStart(
                api_id=12345,
                api_hash="a" * 32,
                phone_number="+79991234567",
            ),
        )
        service.verify(1, TelegramCodeVerify(code="12345"))
        result = service.set_proxy(
            1,
            TelegramProxyInput(
                host="proxy.example.com",
                port=1080,
                username="user",
                password="secret",
            ),
        )
        stored = db.scalar(
            select(TelegramConnection).where(TelegramConnection.user_id == 1)
        )

    assert result.proxy_configured is True
    assert gateway.checked_proxy == {
        "protocol": "SOCKS5",
        "host": "proxy.example.com",
        "port": 1080,
        "username": "user",
        "password": "secret",
    }
    assert stored is not None
    assert "proxy.example.com" not in stored.encrypted_proxy


def test_telegram_webshare_falls_back_from_http_to_socks5(
    client: TestClient, monkeypatch
) -> None:
    class FallbackGateway(_TelegramGateway):
        protocols: list[str] = []

        def check(self, api_id, api_hash, session, proxy):
            self.protocols.append(proxy["protocol"])
            if proxy["protocol"] == "HTTP":
                raise RuntimeError("HTTP tunnel rejected")

    settings = type(
        "Settings",
        (),
        {"provider_secret_key": "t" * 32, "auth_jwt_secret": "j" * 32},
    )()
    monkeypatch.setattr("competitor_intelligence.telegram_connector.get_settings", lambda: settings)
    gateway = FallbackGateway()
    with TestingSession() as db:
        service = TelegramConnectionService(db, gateway)
        service.start(
            1,
            TelegramConnectionStart(
                api_id=12345,
                api_hash="a" * 32,
                phone_number="+79991234567",
            ),
        )
        service.verify(1, TelegramCodeVerify(code="12345"))
        result = service.set_proxy(
            1,
            TelegramProxyInput(
                protocol="HTTP",
                host="p.webshare.io",
                port=80,
                username="user",
                password="secret",
            ),
        )
        stored = db.scalar(
            select(TelegramConnection).where(TelegramConnection.user_id == 1)
        )
        saved_proxy = service._proxy(stored)

    assert result.proxy_configured is True
    assert gateway.protocols == ["HTTP", "SOCKS5"]
    assert saved_proxy["protocol"] == "SOCKS5"
