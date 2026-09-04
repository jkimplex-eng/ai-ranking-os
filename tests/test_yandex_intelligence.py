from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import decision_center.models  # noqa: F401
import execution_engine.models  # noqa: F401
import workspace.models  # noqa: F401
from backend.app.database import Base
from organization_workspace.models import Organization
from yandex_intelligence.models import YandexIntelligenceSnapshot
from yandex_intelligence.service import (
    YandexIntelligenceQuerySource,
    YandexIntelligenceService,
)
from yandex_webmaster.schemas import QueryFactRead, WebmasterEvidenceRead


class WebmasterPort:
    def evidence(self, organization_id: int) -> WebmasterEvidenceRead:
        assert organization_id == 1
        return WebmasterEvidenceRead(
            host_id="https:example.ru:443",
            host_url="https://example.ru/",
            collected_at=datetime.now(UTC),
            query_facts=[
                QueryFactRead(
                    query="лучшая увлажняющая сыворотка",
                    url="https://example.ru/serum",
                    impressions=150,
                    clicks=2,
                    ctr=1.3,
                    position=19,
                    demand=500,
                )
            ],
            diagnostics={"problems": {}},
            indexing={"indicators": {"HTTP_2XX": [{"value": 20}]}},
            external_links={"count": 3},
            sitemaps={"sitemaps": []},
        )


def database() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(Organization(id=1, name="Test", slug="test"))
    db.commit()
    return db


def test_sync_builds_reproducible_query_map_and_action_plan() -> None:
    db = database()
    result = YandexIntelligenceService(db, WebmasterPort()).sync(1)

    assert result.evidence_status == "PARTIAL"
    assert result.query_map[0].query == "лучшая увлажняющая сыворотка"
    assert result.query_map[0].position == 19
    assert result.opportunities[0].priority in {"P0", "P1", "P2"}
    assert "гарантированный" in result.opportunities[0].expected_range
    assert db.query(YandexIntelligenceSnapshot).count() == 1

    snapshot_id, queries = YandexIntelligenceQuerySource(db).queries(
        1, "https://www.example.ru", limit=8
    )
    assert snapshot_id == result.id
    assert queries == ["лучшая увлажняющая сыворотка"]


def test_query_source_does_not_mix_different_sites() -> None:
    db = database()
    YandexIntelligenceService(db, WebmasterPort()).sync(1)
    snapshot_id, queries = YandexIntelligenceQuerySource(db).queries(
        1, "https://other.example", limit=8
    )
    assert snapshot_id == 0
    assert queries == []


def test_yandex_intelligence_is_documented_in_openapi() -> None:
    from backend.app.main import app

    paths = app.openapi()["paths"]
    assert "/integrations/yandex-webmaster/evidence" in paths
    assert "/yandex-intelligence/sync" in paths
    assert "/yandex-intelligence/dashboard" in paths
    assert "/yandex-intelligence/query-seeds" in paths
