import json

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import decision_center.models  # noqa: F401
import execution_engine.models  # noqa: F401
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


def test_wordstat_endpoints_are_documented_in_openapi() -> None:
    from backend.app.main import app

    paths = app.openapi()["paths"]
    assert "/integrations/yandex-wordstat/connection" in paths
    assert "/integrations/yandex-wordstat/discover" in paths
    assert "/integrations/yandex-wordstat/analytics" in paths
