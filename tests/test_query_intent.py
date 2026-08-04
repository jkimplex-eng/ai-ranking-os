from collections.abc import Generator
from datetime import UTC, datetime
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from query_intent.models import (
    ConfidenceHistory,
    IntentClassificationRun,
    IntentHistory,
    RoutingMetadataHistory,
)
from query_intent.pipeline import run_pipeline
from query_intent.schemas import INTENT_SUBTYPES, IntentInput, IntentType

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)
REGRESSION_TIME = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


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


def test_taxonomy_has_ten_primary_intents_and_subtypes() -> None:
    assert len(IntentType) == 10
    assert set(INTENT_SUBTYPES) == set(IntentType)
    assert all(INTENT_SUBTYPES[intent] for intent in IntentType)


def test_multilingual_multi_intent_constraints_and_entities() -> None:
    result = run_pipeline(
        IntentInput(
            request_id="ru-query",
            query="Как выбрать лучший ноутбук до 100000 в Москве?",
        ),
        now=REGRESSION_TIME,
    )

    assert result.language.code == "ru"
    assert {candidate.intent for candidate in result.intents} >= {
        IntentType.RECOMMENDATION,
        IntentType.HOW_TO,
    }
    assert any(item.constraint_type == "PRICE" for item in result.constraints)
    assert any(item.constraint_type == "LANGUAGE" for item in result.constraints)
    assert result.expected_output.format in {"RANKED_LIST", "STEP_BY_STEP"}


def test_regression_comparison_schema_is_stable() -> None:
    payload = IntentInput(
        request_id="regression",
        query="Compare the best laptops under $1500 with reviews",
    )
    first = run_pipeline(payload, now=REGRESSION_TIME)
    second = run_pipeline(payload, now=REGRESSION_TIME)

    assert first.model_dump() == second.model_dump()
    assert first.primary_intent == IntentType.COMPARISON
    assert first.expected_output.format == "COMPARISON_TABLE"
    assert {candidate.intent for candidate in first.intents} >= {
        IntentType.COMPARISON,
        IntentType.RECOMMENDATION,
    }
    assert first.version == "1.0"


def test_injected_llm_fallback_can_resolve_low_confidence_query() -> None:
    class FakeFallback:
        def classify(self, query: str) -> tuple[IntentType, str, float]:
            assert query == "zxqv blorb"
            return IntentType.RESEARCH, "ANALYSIS", 0.93

    result = run_pipeline(
        IntentInput(request_id="fallback", query="zxqv blorb"),
        now=REGRESSION_TIME,
        llm_fallback=FakeFallback(),
    )

    assert result.primary_intent == IntentType.RESEARCH
    assert result.confidence == 0.93
    assert result.routing.strategy == "LLM_FALLBACK"
    assert result.routing.llm_fallback_required is False


def test_integration_classify_get_and_history(client: TestClient) -> None:
    response = client.post(
        "/intent/classify",
        json={
            "request_id": "intent-1",
            "query": "How to fix Python import error?",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["request_id"] == "intent-1"
    assert body["primary_intent"] in {"TROUBLESHOOTING", "HOW_TO"}
    assert len(body["routing"]["rule_scores"]) == 10
    assert len(body["routing"]["embedding_scores"]) == 10
    assert len(body["routing"]["ensemble_scores"]) == 10

    stored = client.get("/intent/intent-1")
    assert stored.status_code == 200
    assert stored.json() == body

    with TestingSession() as session:
        runs = session.scalar(select(func.count()).select_from(IntentClassificationRun))
        intents = session.scalar(select(func.count()).select_from(IntentHistory))
        confidence_rows = session.scalar(
            select(func.count()).select_from(ConfidenceHistory)
        )
        routing_rows = session.scalar(
            select(func.count()).select_from(RoutingMetadataHistory)
        )
    assert runs == 1
    assert intents is not None and intents >= 1
    assert confidence_rows == 31
    assert routing_rows == 1


def test_batch_aliases_arbitrary_queries_and_errors(client: TestClient) -> None:
    response = client.post(
        "/intent/batch",
        json={
            "items": [
                {"request_id": "batch-1", "text": "OpenAI official website"},
                {"request_id": "batch-2", "prompt": "Где купить ноутбук рядом?"},
                {"request_id": "batch-3", "query": "unknown vocabulary qzx"},
            ]
        },
    )
    assert response.status_code == 201
    assert len(response.json()) == 3
    assert response.json()[0]["primary_intent"] == "NAVIGATIONAL"
    assert client.get("/intent/missing").status_code == 404
    assert client.post("/intent/classify", json={"query": ""}).status_code == 422


def test_duplicate_request_id_is_rejected(client: TestClient) -> None:
    payload = {"request_id": "duplicate", "query": "What is AI?"}
    assert client.post("/intent/classify", json=payload).status_code == 201
    assert client.post("/intent/classify", json=payload).status_code == 409


def test_benchmark_pipeline() -> None:
    payload = IntentInput(
        request_id="benchmark",
        query="Compare the best Python frameworks under $100 and explain the differences",
    )
    started = perf_counter()
    for _ in range(1_000):
        run_pipeline(payload, now=REGRESSION_TIME)
    duration = perf_counter() - started

    assert duration < 2.0

