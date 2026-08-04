from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alert.engine import AlertEngine
from alert.models import Alert, AlertEvent, AlertRule
from alert.ports import AlertObservation
from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import Research, ResearchScore

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeAlertSource:
    def __init__(self, observations: list[AlertObservation]) -> None:
        self.observations = observations

    def history(self, entity_id: UUID) -> list[AlertObservation]:
        return self.observations


@pytest.fixture
def db() -> Generator[Session]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(test_engine)


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


def _observations() -> list[AlertObservation]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        AlertObservation(1, start, 40, 60),
        AlertObservation(
            2,
            start + timedelta(days=1),
            80,
            80,
            frozenset({"Brand A"}),
            frozenset({"https://authority.example"}),
        ),
        AlertObservation(
            3,
            start + timedelta(days=2),
            60,
            55,
            critical_recommendations=frozenset({"Repair trust signals"}),
        ),
    ]


def test_engine_evaluates_all_v1_rules_and_persists_events(db: Session) -> None:
    entity_id = uuid4()
    engine = AlertEngine(db, FakeAlertSource(_observations()))

    alerts = engine.evaluate(entity_id)

    assert {item.alert_type for item in alerts} == {
        "VISIBILITY_DROP",
        "TREND_REVERSAL",
        "BRAND_RECOMMENDATION_DISAPPEARED",
        "AUTHORITATIVE_CITATION_DISAPPEARED",
        "CRITICAL_RECOMMENDATION_APPEARED",
        "CONFIDENCE_SHOCK",
    }
    assert all(item.rule_version == "1.0" for item in alerts)
    assert all(item.events[0].event_type == "DETECTED" for item in alerts)
    assert db.scalar(select(func.count(AlertRule.id))) == 6
    assert db.scalar(select(func.count(Alert.id))) == 6
    assert db.scalar(select(func.count(AlertEvent.id))) == 6
    assert len(engine.history(entity_id)) == 6


def test_thresholds_are_rule_driven_and_versioned(db: Session) -> None:
    observations = _observations()
    observations[-1] = AlertObservation(
        3,
        observations[-1].observed_at,
        72,
        68,
        observations[-1].brand_recommendations,
        observations[-1].authoritative_citations,
        observations[-1].critical_recommendations,
    )
    alerts = AlertEngine(db, FakeAlertSource(observations)).evaluate(uuid4())
    kinds = {item.alert_type for item in alerts}
    assert "VISIBILITY_DROP" not in kinds
    assert "CONFIDENCE_SHOCK" not in kinds
    assert "TREND_REVERSAL" in kinds


def _seed_history(entity_id: UUID) -> None:
    start = datetime(2026, 3, 1, tzinfo=UTC)
    with TestingSession() as db:
        for index, visibility in enumerate((70.0, 90.0, 60.0), start=1):
            research = Research(
                entity_id=entity_id,
                title=f"Alert {index}",
                created_at=start + timedelta(days=index),
            )
            db.add(research)
            db.flush()
            db.add(
                ResearchScore(
                    research_id=research.id,
                    mention_score=visibility,
                    recommendation_score=visibility,
                    citation_score=visibility,
                    coverage_score=visibility,
                    confidence_score=visibility,
                    visibility_score=visibility,
                    calculated_at=start + timedelta(days=index),
                    version="1.0",
                )
            )
        db.commit()


def test_alert_api_evaluates_reads_history_and_updates_openapi(client: TestClient) -> None:
    entity_id = uuid4()
    _seed_history(entity_id)

    evaluated = client.post(f"/entities/{entity_id}/alerts/evaluate")
    history = client.get(f"/entities/{entity_id}/alerts")

    assert evaluated.status_code == 201
    assert {item["alert_type"] for item in evaluated.json()} >= {
        "VISIBILITY_DROP", "TREND_REVERSAL", "CONFIDENCE_SHOCK"
    }
    assert history.status_code == 200
    assert history.json() == list(reversed(evaluated.json()))
    paths = client.get("/openapi.json").json()["paths"]
    assert "/entities/{entity_id}/alerts" in paths
    assert "/entities/{entity_id}/alerts/evaluate" in paths


def test_alert_api_validation_and_insufficient_history(client: TestClient) -> None:
    entity_id = uuid4()
    assert client.get(f"/entities/{entity_id}/alerts").json() == []
    assert client.post(f"/entities/{entity_id}/alerts/evaluate").status_code == 409
    assert client.get("/entities/not-a-uuid/alerts").status_code == 422

