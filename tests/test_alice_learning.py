from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import authentication.models  # noqa: F401
import decision_center.models  # noqa: F401
import execution_engine.models  # noqa: F401
import research.models  # noqa: F401
import workspace.models  # noqa: F401
from alice_learning.automation_ports import (
    AutomationLaunchResult,
    AutomationTemplateContext,
)
from alice_learning.automation_repository import AliceAutomationRepository
from alice_learning.automation_schemas import AutomationPlanCreate
from alice_learning.automation_service import AliceAutomationService
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

    other_brand = engine.dashboard(1, "Skillbox")
    assert other_brand.brand == "Skillbox"
    assert other_brand.observation_count == 0
    assert other_brand.recommendation_count == 0


def test_alice_learning_openapi_contract() -> None:
    from backend.app.main import app

    paths = app.openapi()["paths"]
    assert "/alice-learning/observations/{research_id}" in paths
    assert "/alice-learning/train" in paths
    assert "/alice-learning/predict" in paths
    assert "/alice-learning/dashboard" in paths
    assert "/alice-learning/rebuild" in paths
    assert "/alice-learning/models/latest" in paths
    assert "/alice-learning/automation/plans" in paths
    assert "/alice-learning/automation/plans/{plan_id}/run" in paths
    assert "/alice-learning/automation/dashboard" in paths


class AutomationTemplate:
    def context(self, organization_id: int, template_research_id: int, website_url: str):
        return AutomationTemplateContext(
            queries=tuple(
                {"id": str(index), "cluster": cluster, "text": text}
                for index, (cluster, text) in enumerate(
                    [
                        ("category_discovery", "какая сыворотка лучше для сухой кожи"),
                        ("problem_solution", "что помогает при обезвоженной коже"),
                        ("brand_control", "стоит ли покупать Skinjestique"),
                        ("price_comparison", "сыворотки до 3000 рублей"),
                    ]
                )
            ),
            metadata={"query_map_version": "2.0"},
        )


class AutomationLauncher:
    def __init__(self) -> None:
        self.requests = []

    def launch(self, request):
        self.requests.append(request)
        return AutomationLaunchResult(
            research_id=99,
            succeeded=True,
            actual_cost_usd=0.12,
            result={"responses": len(request.queries)},
        )


class AutomationNotifications:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event_type, title, message, **kwargs):
        self.events.append((event_type, title, message, kwargs))


def test_automation_freezes_queries_repeats_three_times_and_records_run() -> None:
    db = database()
    launcher = AutomationLauncher()
    notifications = AutomationNotifications()
    automation = AliceAutomationService(
        AliceAutomationRepository(db), launcher, AutomationTemplate(), notifications
    )
    plan = automation.create(
        1,
        1,
        AutomationPlanCreate(
            template_research_id=10,
            brand="Skinjestique",
            website_url="https://skinjestique.example",
            models=[{"provider": "yandex", "model": "yandexgpt/latest"}],
            daily_budget_usd=10,
            monthly_budget_usd=100,
        ),
    )

    run = automation.run(1, plan.id, "DAILY")

    assert run.status == "COMPLETED"
    assert run.task_count == 12
    assert len(launcher.requests[0].queries) == 12
    assert launcher.requests[0].queries.count("какая сыворотка лучше для сухой кожи") == 3
    assert run.actual_cost_usd == 0.12
    assert notifications.events[-1][0] == "RESEARCH_COMPLETED"
    dashboard = automation.dashboard(1)
    assert dashboard.plans[0].repetitions == 3
    assert "causality" in dashboard.methodology


def test_automation_hard_budget_blocks_provider_call() -> None:
    db = database()
    launcher = AutomationLauncher()
    automation = AliceAutomationService(
        AliceAutomationRepository(db), launcher, AutomationTemplate(), AutomationNotifications()
    )
    plan = automation.create(
        1,
        1,
        AutomationPlanCreate(
            template_research_id=10,
            brand="Skinjestique",
            website_url="https://skinjestique.example",
            models=[{"provider": "yandex", "model": "yandexgpt/latest"}],
            daily_budget_usd=0.01,
            monthly_budget_usd=1,
        ),
    )

    run = automation.run(1, plan.id, "DAILY")

    assert run.status == "BUDGET_BLOCKED"
    assert launcher.requests == []
