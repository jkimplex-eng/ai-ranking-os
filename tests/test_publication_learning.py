from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app  # noqa: F401
from publication_learning.service import PublicationLearningService
from research.models import (
    Research,
    ResearchScore,
    ResearchStatus,
    ResearchTask,
    Response,
    ResponseProcessingStatus,
)
from research_lab.models import ResearchPublication


def _engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _research(
    db: Session,
    *,
    entity_id: object,
    created_at: datetime,
    visibility: float,
    query: str = "Какую сыворотку выбрать?",
) -> Research:
    item = Research(
        entity_id=entity_id,
        title="Skinjestique",
        status=ResearchStatus.COMPLETED,
        metadata_payload={
            "target_entity": "Skinjestique",
            "query_catalog": [{"text": query}],
            "languages": ["ru"],
            "regions": ["RU"],
            "research_profile": "BEAUTY",
        },
        total_tasks=1,
        completed_tasks=1,
        progress_percent=100,
        created_at=created_at,
        updated_at=created_at,
    )
    item.tasks.append(ResearchTask(query=query, provider="yandex", model="yandexgpt-pro"))
    item.scores.append(
        ResearchScore(
            mention_score=visibility,
            recommendation_score=visibility,
            citation_score=visibility,
            coverage_score=100,
            confidence_score=80,
            visibility_score=visibility,
            version="1.2",
            calculated_at=created_at,
        )
    )
    db.add(item)
    db.flush()
    return item


def test_learning_matches_same_matrix_and_builds_versioned_estimate() -> None:
    engine = _engine()
    Base.metadata.create_all(engine)
    entity_id = uuid4()
    with Session(engine) as db:
        baseline = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            visibility=30,
        )
        publication = ResearchPublication(
            entity_id=entity_id,
            research_id=baseline.id,
            url="https://media.example/article",
            content_hash="a" * 64,
            title="Экспертный материал",
            channel="EARNED",
            content_type="ARTICLE",
            target_queries=["Какую сыворотку выбрать?"],
            metadata_payload={},
            published_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        db.add(publication)
        followup = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 1, 3, tzinfo=UTC),
            visibility=45,
        )
        followup.tasks[0].responses.append(
            Response(
                provider="yandex",
                model="yandexgpt-pro",
                content="Источник: https://media.example/article",
                prompt="Какую сыворотку выбрать?",
                normalized_response={"citations": ["https://media.example/article"]},
                processing_status=ResponseProcessingStatus.PROCESSED,
                finished_at=datetime(2026, 1, 3, tzinfo=UTC),
            )
        )
        db.commit()

        experiments = PublicationLearningService(db).evaluate_followup(followup.id)
        summary = PublicationLearningService(db).summary(entity_id)

        assert len(experiments) == 1
        assert experiments[0].baseline_research_id == baseline.id
        assert experiments[0].metric_deltas["visibility_score"] == 15
        assert experiments[0].causality_status == "OBSERVED_ASSOCIATION"
        db.refresh(publication, ["observations"])
        assert len(publication.observations) == 1
        assert publication.observations[0].provider == "yandex"
        estimate = next(
            item for item in summary["influence_estimates"] if item.metric == "visibility_score"
        )
        assert estimate.resource_domain == "media.example"
        assert estimate.expected_delta == 15
        assert estimate.sample_size == 1
        assert estimate.evidence_grade == "PRELIMINARY"


def test_learning_rejects_changed_query_matrix() -> None:
    engine = _engine()
    Base.metadata.create_all(engine)
    entity_id = uuid4()
    with Session(engine) as db:
        baseline = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            visibility=30,
        )
        db.add(
            ResearchPublication(
                entity_id=entity_id,
                research_id=baseline.id,
                url="https://media.example/article",
                content_hash="b" * 64,
                title="Материал",
                channel="EARNED",
                content_type="ARTICLE",
                target_queries=[],
                metadata_payload={},
                published_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
        )
        followup = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 1, 3, tzinfo=UTC),
            visibility=50,
            query="Какой крем выбрать?",
        )
        db.commit()

        assert PublicationLearningService(db).evaluate_followup(followup.id) == []


def test_publication_learning_api_and_openapi(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _engine()
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(
        "backend.app.main.hydrate_provider_credentials",
        lambda *_args, **_kwargs: None,
    )
    app.dependency_overrides[get_db] = override_db
    entity_id = uuid4()
    with TestClient(app) as client:
        summary = client.get(f"/publication-learning/entity/{entity_id}")
        assert summary.status_code == 200
        assert summary.json()["status"] == "INSUFFICIENT_DATA"
        paths = client.get("/openapi.json").json()["paths"]
        assert "/publication-learning/evaluate/{research_id}" in paths
        assert "/publication-learning/entity/{entity_id}" in paths
        assert "/publication-learning/influence" in paths
    app.dependency_overrides.clear()
