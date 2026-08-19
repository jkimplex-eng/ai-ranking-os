from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app  # noqa: F401
from publication_learning.models import PublicationExperiment
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
    task = ResearchTask(query=query, provider="yandex", model="yandexgpt-pro")
    task.responses.append(
        Response(
            provider="yandex",
            model="yandexgpt-pro",
            content="Skinjestique упомянут в ответе.",
            prompt=query,
            normalized_response={"citations": []},
            processing_status=ResponseProcessingStatus.PROCESSED,
            finished_at=created_at,
        )
    )
    item.tasks.append(task)
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
        assert experiments[0].evidence_level == "OBSERVATION"
        assert experiments[0].matched_pairs == 1
        assert experiments[0].evidence_matrix["pairs"][0]["eligible"] is True
        assert experiments[0].confidence_method == "MATCHED_RESPONSE_COVERAGE_V1"
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
        assert estimate.evidence_level == "OBSERVATION"
        assert estimate.positive_experiments == 1
        assert estimate.negative_experiments == 0
        assert estimate.confidence_min <= estimate.expected_delta <= estimate.confidence_max


def test_unobserved_publication_stays_hypothesis_and_does_not_train_venue() -> None:
    engine = _engine()
    Base.metadata.create_all(engine)
    entity_id = uuid4()
    with Session(engine) as db:
        baseline = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 2, 1, tzinfo=UTC),
            visibility=30,
        )
        db.add(
            ResearchPublication(
                entity_id=entity_id,
                research_id=baseline.id,
                url="https://unseen.example/article",
                content_hash="c" * 64,
                title="Материал без обнаружения",
                channel="EARNED",
                content_type="ARTICLE",
                target_queries=["Какую сыворотку выбрать?"],
                metadata_payload={},
                published_at=datetime(2026, 2, 2, tzinfo=UTC),
            )
        )
        followup = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 2, 3, tzinfo=UTC),
            visibility=60,
        )
        db.commit()

        experiment = PublicationLearningService(db).evaluate_followup(followup.id)[0]
        summary = PublicationLearningService(db).summary(entity_id)

        assert experiment.evidence_level == "HYPOTHESIS"
        assert experiment.causality_status == "UNVERIFIED_TIMING_ASSOCIATION"
        assert summary["influence_estimates"] == []
        assert "не обнаружен" in experiment.limitations[0]


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


def test_learning_subtracts_control_query_drift() -> None:
    engine = _engine()
    Base.metadata.create_all(engine)
    entity_id = uuid4()
    target_query = "Какую увлажняющую сыворотку выбрать?"
    control_query = "Как выбрать солнцезащитный крем?"
    with Session(engine) as db:
        baseline = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 4, 1, tzinfo=UTC),
            visibility=20,
            query=target_query,
        )
        baseline.metadata_payload["query_catalog"] = [
            {"text": target_query},
            {"text": control_query},
        ]
        baseline.tasks.append(
            ResearchTask(
                query=control_query,
                provider="yandex",
                model="yandexgpt-pro",
                responses=[
                    Response(
                        provider="yandex",
                        model="yandexgpt-pro",
                        content="Нейтральный контрольный ответ.",
                        prompt=control_query,
                        normalized_response={"citations": []},
                        processing_status=ResponseProcessingStatus.PROCESSED,
                        finished_at=datetime(2026, 4, 1, tzinfo=UTC),
                    )
                ],
            )
        )
        publication = ResearchPublication(
            entity_id=entity_id,
            research_id=baseline.id,
            url="https://controlled.example/serum",
            content_hash="d" * 64,
            title="Материал о сыворотках",
            channel="EARNED",
            content_type="ARTICLE",
            target_queries=[target_query],
            metadata_payload={},
            published_at=datetime(2026, 4, 2, tzinfo=UTC),
        )
        followup = _research(
            db,
            entity_id=entity_id,
            created_at=datetime(2026, 4, 3, tzinfo=UTC),
            visibility=50,
            query=target_query,
        )
        followup.metadata_payload["query_catalog"] = [
            {"text": target_query},
            {"text": control_query},
        ]
        target_response = followup.tasks[0].responses[0]
        target_response.content = "Источник: https://controlled.example/serum"
        target_response.normalized_response = {
            "citations": ["https://controlled.example/serum"]
        }
        followup.tasks.append(
            ResearchTask(
                query=control_query,
                provider="yandex",
                model="yandexgpt-pro",
                responses=[
                    Response(
                        provider="yandex",
                        model="yandexgpt-pro",
                        content="Нейтральный контрольный ответ.",
                        prompt=control_query,
                        normalized_response={"citations": []},
                        processing_status=ResponseProcessingStatus.PROCESSED,
                        finished_at=datetime(2026, 4, 3, tzinfo=UTC),
                    )
                ],
            )
        )
        db.add(publication)
        db.commit()

        experiment = PublicationLearningService(db).evaluate_followup(followup.id)[0]

        assert experiment.design_type == "MATCHED_DIFFERENCE_IN_DIFFERENCES"
        assert experiment.effect_method == "QUERY_LEVEL_DIFFERENCE_IN_DIFFERENCES_V1"
        assert experiment.treatment_pairs == 1
        assert experiment.control_pairs == 1
        assert experiment.adjusted_metric_deltas["citation_score"] == 100
        assert experiment.provider_deltas["yandex/yandexgpt-pro"]["citation_score"] == 100
        assert experiment.evidence_matrix["controlled_provider_keys"] == [
            "yandex/yandexgpt-pro"
        ]
        assert experiment.evidence_level == "CONTROLLED"
        assert experiment.causality_status == "CONTROLLED_ASSOCIATION"
        provider_estimate = next(
            item
            for item in PublicationLearningService(db).repository.estimates(
                {"algorithm_version": "1.2", "provider": "yandex", "metric": "citation_score"}
            )
        )
        assert provider_estimate.expected_delta == 100
        assert provider_estimate.controlled_experiments == 1
        assert provider_estimate.effect_method == "QUERY_LEVEL_DIFFERENCE_IN_DIFFERENCES_V1"


def test_repeated_observations_upgrade_domain_to_correlation() -> None:
    engine = _engine()
    Base.metadata.create_all(engine)
    entity_id = uuid4()
    with Session(engine) as db:
        for index, delta in enumerate((8.0, 12.0, 16.0), start=1):
            baseline = _research(
                db,
                entity_id=entity_id,
                created_at=datetime(2026, 3, index * 2 - 1, tzinfo=UTC),
                visibility=30,
            )
            publication = ResearchPublication(
                entity_id=entity_id,
                research_id=baseline.id,
                url=f"https://repeat.example/article-{index}",
                content_hash=str(index) * 64,
                title=f"Материал {index}",
                channel="EARNED",
                content_type="ARTICLE",
                target_queries=["Какую сыворотку выбрать?"],
                metadata_payload={},
                published_at=datetime(2026, 3, index * 2, tzinfo=UTC),
            )
            followup = _research(
                db,
                entity_id=entity_id,
                created_at=datetime(2026, 3, index * 2, 12, tzinfo=UTC),
                visibility=30 + delta,
            )
            db.add(publication)
            db.flush()
            db.add(
                PublicationExperiment(
                    publication_id=publication.id,
                    entity_id=entity_id,
                    baseline_research_id=baseline.id,
                    followup_research_id=followup.id,
                    matrix_fingerprint=f"matrix-{index}",
                    status="MATCHED",
                    causality_status="OBSERVED_ASSOCIATION",
                    evidence_grade="PRELIMINARY",
                    evidence_level="OBSERVATION",
                    metric_deltas={"visibility_score": delta},
                    provider_deltas={},
                    sample_size=3,
                    baseline_sample_size=3,
                    followup_sample_size=3,
                    matched_pairs=3,
                    failed_responses=0,
                    confidence_score=0.7,
                    confidence_method="MATCHED_RESPONSE_COVERAGE_V1",
                    evidence_matrix={},
                    limitations=[],
                    algorithm_version="1.2",
                    evaluated_at=datetime(2026, 3, index * 2, 13, tzinfo=UTC),
                )
            )
        db.commit()

        PublicationLearningService(db)._rebuild_estimates()
        estimate = PublicationLearningService(db).repository.estimates()[0]

        assert estimate.resource_domain == "repeat.example"
        assert estimate.evidence_level == "CORRELATION"
        assert estimate.sample_size == 3
        assert estimate.positive_experiments == 3
        assert estimate.negative_experiments == 0
        assert estimate.confidence_min <= 12 <= estimate.confidence_max


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
        assert "/publication-learning/experiments/{experiment_id}" in paths
        missing = client.get("/publication-learning/experiments/999")
        assert missing.status_code == 404
    app.dependency_overrides.clear()
