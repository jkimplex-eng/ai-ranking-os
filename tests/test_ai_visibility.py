from collections.abc import Generator
from datetime import UTC, datetime
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ai_visibility.calculator import calculate_visibility_score
from ai_visibility.metrics import calculate_metrics
from ai_visibility.models import VisibilityCalculation, VisibilityWeightSet
from ai_visibility.pipeline import run_pipeline
from ai_visibility.schemas import VisibilityInput
from ai_visibility.weights import DEFAULT_WEIGHTS
from backend.app.database import Base, get_db
from backend.app.main import app

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)
REGRESSION_TIME = datetime(2026, 1, 31, tzinfo=UTC)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(test_engine)

    def override_get_db() -> Generator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def regression_payload() -> VisibilityInput:
    return VisibilityInput.model_validate(
        {
            "entity_id": "skinjestique",
            "entity": "Skinjestique",
            "observations": [
                {
                    "model": model,
                    "mentioned": True,
                    "recommendation_position": position,
                    "citations": [0.8, 0.8, 0.8],
                    "entity_confidence": 0.9,
                    "observed_at": REGRESSION_TIME.isoformat(),
                }
                for model, position in zip(
                    ["codex", "qwen", "deepseek", "claude", "gemini"],
                    [1, 2, 3, 4, 5],
                    strict=True,
                )
            ],
        }
    )


def test_unit_metric_calculation_and_weighting() -> None:
    payload = regression_payload()
    metrics = calculate_metrics(payload, now=REGRESSION_TIME)

    assert metrics == {
        "mention_frequency": 100.0,
        "recommendation_position": 50.0,
        "citation_count": 100.0,
        "citation_authority": 80.0,
        "cross_model_presence": 100.0,
        "consistency": 100.0,
        "entity_confidence": 90.0,
        "freshness": 100.0,
    }
    assert calculate_visibility_score(metrics, DEFAULT_WEIGHTS) == 88.5


def test_regression_score_and_confidence_are_stable() -> None:
    result = run_pipeline(regression_payload(), now=REGRESSION_TIME)

    assert result.visibility_score == 88.5
    assert result.confidence == 0.81
    assert result.version == "1.0"


def test_integration_calculate_get_and_history(client: TestClient) -> None:
    payload = regression_payload().model_dump(mode="json")
    response = client.post("/visibility/calculate", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["entity"] == "Skinjestique"
    assert 0 <= body["visibility_score"] <= 100
    assert 0 <= body["confidence"] <= 1
    assert set(body["metrics"]) == set(DEFAULT_WEIGHTS)
    assert body["weights"] == DEFAULT_WEIGHTS
    assert body["version"] == "1.0"

    latest = client.get("/visibility/skinjestique")
    assert latest.status_code == 200
    assert latest.json()["visibility_score"] == body["visibility_score"]

    with TestingSession() as session:
        calculations = session.scalar(
            select(func.count()).select_from(VisibilityCalculation)
        )
        versions = session.scalar(select(func.count()).select_from(VisibilityWeightSet))
    assert calculations == 1
    assert versions == 1


def test_batch_accepts_task_201_compatible_aliases(client: TestClient) -> None:
    response = client.post(
        "/visibility/batch",
        json={
            "items": [
                {
                    "brand": "Alias Brand",
                    "entity_extraction_result": {
                        "id": "alias-brand",
                        "responses": [
                            {
                                "provider": "qwen",
                                "is_mentioned": True,
                                "rank": 2,
                                "citations": 2,
                                "extraction_confidence": 0.8,
                            }
                        ],
                    },
                    "task_201_extension": {"preserved": True},
                },
                regression_payload().model_dump(mode="json"),
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 2
    assert body[0]["entity_id"] == "alias-brand"
    assert body[0]["entity"] == "Alias Brand"


def test_invalid_input_and_missing_entity_history(client: TestClient) -> None:
    assert client.post("/visibility/calculate", json={"entity": "No data"}).status_code == 422
    assert client.get("/visibility/missing").status_code == 404


def test_benchmark_pipeline_throughput() -> None:
    payload = regression_payload()
    started = perf_counter()
    for _ in range(2_000):
        run_pipeline(payload, now=REGRESSION_TIME)
    duration = perf_counter() - started

    assert duration < 2.0
