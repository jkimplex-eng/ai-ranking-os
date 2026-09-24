from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import decision_center.models  # noqa: F401
import execution_engine.models  # noqa: F401
import workspace.models  # noqa: F401
from backend.app.config import Settings
from backend.app.database import Base
from organization_workspace.models import Organization
from provider_connections.crypto import SecretCipher
from yandex_webmaster.repository import YandexWebmasterRepository
from yandex_webmaster.service import YandexWebmasterError, YandexWebmasterService


class Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self.payload


class YandexClient:
    def __init__(self) -> None:
        self.token_data: dict | None = None

    def post(self, url: str, *, data: dict):
        assert url.endswith("/token")
        self.token_data = data
        return Response(
            {"access_token": "oauth-access-secret", "refresh_token": "oauth-refresh-secret"}
        )

    def get(self, url: str, *, headers: dict, params: dict | None = None):
        assert headers["Authorization"] == "OAuth oauth-access-secret"
        if url.endswith("/user"):
            return Response({"user_id": 42})
        if url.endswith("/hosts"):
            return Response(
                {
                    "hosts": [
                        {
                            "host_id": "https:example.ru:443",
                            "ascii_host_url": "https://example.ru/",
                            "verification": {"verification_state": "VERIFIED"},
                        }
                    ]
                }
            )
        assert params == {"query_indicator": "TOTAL_SHOWS", "limit": 50}
        return Response(
            {
                "queries": [
                    {
                        "query_id": 7,
                        "query_text": "лучшая увлажняющая сыворотка",
                        "indicators": {"TOTAL_SHOWS": 120},
                    }
                ]
            }
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None,
        json: dict | None,
        headers: dict,
    ):
        assert headers["Authorization"] == "OAuth oauth-access-secret"
        if url.endswith("query-analytics/list"):
            assert method == "POST" and json and json["text_indicator"] == "QUERY"
            return Response(
                {
                    "text_indicator_to_statistics": [
                        {
                            "text_indicator": {
                                "type": "QUERY",
                                "value": "лучшая увлажняющая сыворотка",
                            },
                            "popular_complementary_indicator": {
                                "type": "URL",
                                "value": "https://example.ru/serum",
                            },
                            "statistics": [
                                {"date": "2026-08-19", "field": "IMPRESSIONS", "value": 120},
                                {"date": "2026-08-19", "field": "POSITION", "value": 18},
                            ],
                        }
                    ]
                }
            )
        if url.endswith("diagnostics"):
            return Response({"problems": {}})
        if url.endswith("indexing/history"):
            return Response({"indicators": {"HTTP_2XX": [{"value": 10}]}})
        if url.endswith("links/external/samples"):
            return Response({"count": 1, "links": [{"source_url": "https://media.ru"}]})
        if url.endswith("sitemaps"):
            return Response({"sitemaps": [{"sitemap_url": "https://example.ru/sitemap.xml"}]})
        raise AssertionError(url)


def service() -> tuple[YandexWebmasterService, Session, YandexClient]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(Organization(id=1, name="Test", slug="test"))
    db.commit()
    client = YandexClient()
    settings = Settings(
        database_url="sqlite:///:memory:",
        yandex_webmaster_client_id="client-id",
        yandex_webmaster_client_secret="server-only-secret",
        yandex_webmaster_redirect_uri="https://app.example/api/integrations/yandex-webmaster/callback",
    )
    return (
        YandexWebmasterService(
            YandexWebmasterRepository(db), SecretCipher("x" * 40), settings, client
        ),
        db,
        client,
    )


def test_oauth_connects_encrypts_tokens_and_reads_real_webmaster_data() -> None:
    webmaster, _, client = service()
    authorization_url = webmaster.authorization_url(1, 9)
    query = parse_qs(urlparse(authorization_url).query)

    assert query["scope"] == ["webmaster:hostinfo"]
    assert query["code_challenge_method"] == ["S256"]
    connection = webmaster.complete("authorization-code", query["state"][0])

    assert connection.status == "CONNECTED"
    assert "oauth-access-secret" not in connection.access_token_ciphertext
    assert client.token_data is not None
    assert client.token_data["code_verifier"] != query["code_challenge"][0]
    hosts = webmaster.hosts(1)
    assert hosts[0].verified is True
    webmaster.select_host(1, hosts[0].host_id, hosts[0].ascii_host_url)
    queries = webmaster.popular_queries(1, 50)
    assert queries[0].query_text == "лучшая увлажняющая сыворотка"
    assert queries[0].indicators["TOTAL_SHOWS"] == 120
    evidence = webmaster.evidence(1)
    assert evidence.query_facts[0].position == 18
    assert evidence.external_links["count"] == 1
    assert evidence.partial_errors == {}


def test_oauth_state_is_single_use() -> None:
    webmaster, _, _ = service()
    authorization_url = webmaster.authorization_url(1, 9)
    state = parse_qs(urlparse(authorization_url).query)["state"][0]
    webmaster.complete("authorization-code", state)
    with pytest.raises(YandexWebmasterError, match="недействительна"):
        webmaster.complete("authorization-code", state)


def test_missing_server_secret_fails_without_leaking_configuration() -> None:
    webmaster, _, _ = service()
    webmaster.settings.yandex_webmaster_client_secret = None
    with pytest.raises(YandexWebmasterError, match="отсутствует"):
        webmaster.authorization_url(1, 9)
