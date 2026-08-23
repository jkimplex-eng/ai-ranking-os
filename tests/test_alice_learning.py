from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import decision_center.models  # noqa: F401
import execution_engine.models  # noqa: F401
import research.models  # noqa: F401
import workspace.models  # noqa: F401
from alice_learning.ports import AliceEvidenceRecord
from alice_learning.repository import AliceLearningRepository
from alice_learning.schemas import FEATURE_NAMES, PredictRequest, TrainRequest
from alice_learning.service import AliceLearningService
from backend.app.database import Base
from organization_workspace.models import Organization


class EvidencePort:
    def __init__(self, count: int) -> None:
        self.count = count

    def records(self, organization_id: int, research_id: int) -> list[AliceEvidenceRecord]:
        assert organization_id == 1
        result = []
        for index in range(self.count):
            recommended = index % 2 == 0
            signal = 0.9 if recommended else 0.1
            features = {name: signal for name in FEATURE_NAMES}
            result.append(
                AliceEvidenceRecord(
                    research_id=research_id,
                    response_id=index + 1,
                    brand="Skinjestique",
                    query=f"покупательский запрос {index}",
                    category="UNIVERSAL",
                    language="ru",
                    region="RU",
                    provider="yandex",
                    model="yandexgpt/latest",
                    mentioned=recommended,
                    recommended=recommended,
                    cited=recommended,
                    recommendation_rank=1 if recommended else None,
                    source_domains=["example.ru"] if recommended else [],
                    features=features,
                    feature_evidence={
                        name: {"status": "MEASURED", "source": "test", "value": signal}
                        for name in FEATURE_NAMES
                    },
                    evidence_status="MEASURED",
                    observed_at=datetime.now(UTC),
                )
            )
        return result


class InfluencePort:
    def factors(self, *, category: str, language: str, region: str) -> list[dict]:
        return [
            {
                "resource_domain": "industry.example",
                "expected_delta": 8.0,
                "confidence_min": 2.0,
                "confidence_max": 14.0,
                "confidence_score": 0.7,
                "sample_size": 3,
                "evidence_level": "CORRELATION",
                "controlled_experiments": 1,
                "algorithm_version": "1.2",
            }
        ]


def database() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(Organization(id=1, name="Test", slug="test"))
    db.commit()
    return db


def service(db: Session, count: int) -> AliceLearningService:
    return AliceLearningService(
        db,
        EvidencePort(count),
        InfluencePort(),
        AliceLearningRepository(db),
    )


def test_training_refuses_to_invent_effects_for_small_sample() -> None:
    db = database()
    engine = service(db, 4)
    assert len(engine.ingest(1, 10)) == 4
    model = engine.train(1, TrainRequest())

    assert model.status == "INSUFFICIENT_SAMPLE"
    assert model.sample_size == 4
    prediction = engine.predict(
        1,
        PredictRequest(
            brand="Skinjestique",
            query="какая сыворотка лучше",
            features={name: 0.2 for name in FEATURE_NAMES},
        ),
    )
    assert prediction.evidence_status == "INSUFFICIENT_SAMPLE"
    assert prediction.counterfactuals == []
    assert prediction.confidence <= 0.15


def test_model_learns_direction_and_produces_explainable_counterfactuals() -> None:
    db = database()
    engine = service(db, 20)
    engine.ingest(1, 20)
    engine.ingest(1, 20)
    model = engine.train(1, TrainRequest())

    assert model.status == "READY"
    assert model.sample_size == 20
    assert all(value > 0 for value in model.coefficients.values())
    prediction = engine.predict(
        1,
        PredictRequest(
            brand="Skinjestique",
            query="сыворотка для чувствительной кожи",
            features={name: 0.1 for name in FEATURE_NAMES},
        ),
    )

    assert prediction.evidence_status == "MODELLED"
    assert prediction.counterfactuals
    assert all(
        item["predicted_probability"] > item["current_probability"]
        for item in prediction.counterfactuals
    )
    assert prediction.explanation["sample"]["total"] == 20
    assert (
        prediction.explanation["confirmed_publication_factors"][0]["resource_domain"]
        == "industry.example"
    )
    dashboard = engine.dashboard(1)
    assert dashboard.observation_count == 20
    assert dashboard.brand == "Skinjestique"
    assert dashboard.baseline_probability is not None
    assert dashboard.recommended_actions


def test_alice_learning_openapi_contract() -> None:
    from backend.app.main import app

    paths = app.openapi()["paths"]
    assert "/alice-learning/observations/{research_id}" in paths
    assert "/alice-learning/train" in paths
    assert "/alice-learning/predict" in paths
    assert "/alice-learning/dashboard" in paths
    assert "/alice-learning/rebuild" in paths
    assert "/alice-learning/models/latest" in paths
