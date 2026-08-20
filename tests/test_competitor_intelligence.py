from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from competitor_intelligence.schemas import SocialSourceCreate
from competitor_intelligence.social_monitor import (
    CollectedPost,
    CompetitorSocialMonitorService,
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
