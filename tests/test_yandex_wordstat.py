import json

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import authentication.models  # noqa: F401
import decision_center.models  # noqa: F401
import execution_engine.models  # noqa: F401
import recommendation.simulation.models  # noqa: F401
import recommendation.templates.models  # noqa: F401
import workspace.models  # noqa: F401
from backend.app.database import Base
from organization_workspace.models import Organization
from provider_connections.crypto import SecretCipher
from yandex_wordstat.models import WordstatConnection
from yandex_wordstat.repository import WordstatRepository
from yandex_wordstat.schemas import WordstatDiscoveryRequest
from yandex_wordstat.service import WordstatQuerySource, WordstatService


def database() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(Organization(id=1, name="Test", slug="test"))
    db.commit()
    return db


def client(requests: list[httpx.Request]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if json.loads(request.content)["phrase"] == "яндекс":
            return httpx.Response(200, json={"results": []})
        return httpx.Response(
            200,
            json={
                "totalCount": "1000",
                "results": [
                    {"phrase": "курсы дизайна", "count": "900"},
                    {"phrase": "Skillbox дизайн", "count": "100"},
                ],
                "associations": [{"phrase": "обучение дизайну", "count": "500"}],
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_connect_and_discover_use_official_search_api_contract() -> None:
    db = database()
    requests: list[httpx.Request] = []
    service = WordstatService(
        db,
        WordstatRepository(db),
        SecretCipher("x" * 32),
        client(requests),
    )

    connection = service.connect(1, 7, "folder-1", "API_KEY", "secret-api-key")
    snapshot = service.discover(
        1,
        7,
        WordstatDiscoveryRequest(
            brand="Skillbox",
            category="дизайн",
            region_ids=[213],
            device="all",
            limit=5,
        ),
    )

    assert connection.connected is True
    assert requests[-1].url.path == "/v2/wordstat/topRequests"
    assert requests[-1].headers["Authorization"] == "Api-key secret-api-key"
    assert json.loads(requests[-1].content) == {
        "phrase": "дизайн",
        "numPhrases": 15,
        "devices": ["DEVICE_ALL"],
        "folderId": "folder-1",
        "regions": ["213"],
    }
    assert [item.query for item in snapshot.queries] == [
        "курсы дизайна",
        "обучение дизайну",
        "Skillbox дизайн",
    ]
    stored = db.query(WordstatConnection).one()
    assert "secret-api-key" not in stored.credential_ciphertext

    snapshot_id, queries = WordstatQuerySource(db).queries(1, "Skillbox")
    assert snapshot_id == snapshot.id
    assert queries == ["курсы дизайна", "обучение дизайну"]


def test_wordstat_filters_ambiguous_association_noise() -> None:
    db = database()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [{"phrase": "geo продвижение сайта", "count": "253"}],
                "associations": [
                    {"phrase": "гео история", "count": "1912"},
                    {"phrase": "реклама и связи с общественностью", "count": "2594"},
                    {"phrase": "туториал продвинутого игрока", "count": "361"},
                    {"phrase": "услуги продвижения", "count": "120"},
                ],
            },
        )

    service = WordstatService(
        db,
        WordstatRepository(db),
        SecretCipher("x" * 32),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    service.connect(1, 7, "folder-1", "API_KEY", "secret-api-key")
    snapshot = service.discover(
        1,
        7,
        WordstatDiscoveryRequest(
            brand="AI Ranking OS",
            category="GEO-продвижение",
            limit=30,
        ),
    )

    assert [item.query for item in snapshot.queries] == [
        "geo продвижение сайта",
        "услуги продвижения",
    ]
    assert snapshot.algorithm_version == "1.1"


def test_wordstat_rejects_tokenized_punycode_query() -> None:
    assert WordstatService._query_well_formed("geo продвижение xn d1abiikjcedki") is False
    assert WordstatService._query_well_formed("geo продвижение сайта") is True


def test_wordstat_endpoints_are_documented_in_openapi() -> None:
    from backend.app.main import app

    paths = app.openapi()["paths"]
    assert "/integrations/yandex-wordstat/connection" in paths
    assert "/integrations/yandex-wordstat/discover" in paths
    assert "/integrations/yandex-wordstat/analytics" in paths


def test_wordstat_accepts_all_query_sizes_offered_by_the_ui() -> None:
    for limit in (30, 50, 100):
        payload = WordstatDiscoveryRequest(
            brand="AI Ranking OS",
            category="GEO продвижение",
            limit=limit,
        )
        assert payload.limit == limit


def test_platform_wordstat_connection_is_available_to_isolated_client() -> None:
    db = database()
    db.add(Organization(id=2, name="Platform", slug="platform"))
    db.commit()
    requests: list[httpx.Request] = []
    service = WordstatService(
        db,
        WordstatRepository(db),
        SecretCipher("x" * 32),
        client(requests),
        platform_organization_id=2,
    )
    service.connect(2, 7, "platform-folder", "API_KEY", "platform-secret-key")

    status = service.status(1)
    snapshot = service.discover(
        1,
        8,
        WordstatDiscoveryRequest(brand="Клиент", category="дизайн", limit=5),
    )

    assert status.connected is True
    assert status.managed_by_platform is True
    assert status.folder_id is None
    assert snapshot.organization_id == 1
    assert json.loads(requests[-1].content)["folderId"] == "platform-folder"
    assert WordstatRepository(db).snapshot(1, snapshot.id) is not None
    assert WordstatRepository(db).snapshot(2, snapshot.id) is None
