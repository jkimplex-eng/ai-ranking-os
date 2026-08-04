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
from entity_extraction.entity_types import EntityType
from entity_extraction.models import (
    EntityExtractionRun,
    EntityHistory,
    RelationHistory,
)
from entity_extraction.pipeline import run_pipeline
from entity_extraction.relations import RelationType
from entity_extraction.schemas import ExtractionInput

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


def structured_payload(response_id: str = "response-203") -> dict:
    return {
        "response_id": response_id,
        "model": "codex",
        "raw_response": {
            "text": "IBM partners with OpenAI.",
            "entities": [
                {
                    "id": "e1",
                    "name": "IBM",
                    "type": "ORGANIZATION",
                    "confidence": 0.91,
                },
                {
                    "id": "e2",
                    "name": "International Business Machines",
                    "type": "ORGANIZATION",
                    "confidence": 0.95,
                },
                {
                    "id": "e3",
                    "name": "OpenAI",
                    "type": "ORG",
                    "confidence": 0.98,
                    "kg_id": "kg:openai",
                },
            ],
            "relations": [
                {
                    "source": "e1",
                    "target": "e3",
                    "type": "PARTNERS_WITH",
                    "confidence": 0.9,
                }
            ],
        },
    }


def test_supported_taxonomy_sizes() -> None:
    assert len(EntityType) == 16
    assert len(RelationType) >= 25


def test_unit_raw_text_entity_and_relation_extraction() -> None:
    result = run_pipeline(
        ExtractionInput(
            response_id="raw-1",
            raw_response=(
                "Sam Altman works for OpenAI Inc. Contact team@example.com "
                "or visit https://example.com on 2026-07-29."
            ),
        ),
        now=REGRESSION_TIME,
    )

    names = {entity.canonical_name for entity in result.entities}
    types = {entity.entity_type for entity in result.entities}
    assert "Sam Altman" in names
    assert "OpenAI" in names
    assert EntityType.EMAIL in types
    assert EntityType.URL in types
    assert EntityType.DATE in types
    assert any(relation.relation_type == "WORKS_FOR" for relation in result.relations)
    assert all(entity.knowledge_graph_id.startswith("kg:") for entity in result.entities)


def test_alias_resolution_deduplication_and_relation_remap() -> None:
    result = run_pipeline(
        ExtractionInput.model_validate(structured_payload()),
        now=REGRESSION_TIME,
    )

    assert len(result.entities) == 2
    ibm = next(
        entity
        for entity in result.entities
        if entity.canonical_name == "International Business Machines"
    )
    assert "IBM" in ibm.aliases
    assert len(result.relations) == 1
    assert result.relations[0].relation_type == "PARTNERS_WITH"
    assert any(log.stage == "alias_resolution" for log in result.resolution_logs)


def test_regression_schema_and_ids_are_stable() -> None:
    payload = ExtractionInput.model_validate(structured_payload("stable"))
    first = run_pipeline(payload, now=REGRESSION_TIME)
    second = run_pipeline(payload, now=REGRESSION_TIME)

    assert first.model_dump() == second.model_dump()
    assert first.version == "1.0"
    assert first.model_dump().keys() == {
        "response_id",
        "entities",
        "relations",
        "resolution_logs",
        "version",
        "processed_at",
    }


def test_integration_extract_get_and_database_history(client: TestClient) -> None:
    response = client.post("/entity-extraction/extract", json=structured_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["response_id"] == "response-203"
    assert len(body["entities"]) == 2
    assert len(body["relations"]) == 1

    stored = client.get("/entity-extraction/response-203")
    assert stored.status_code == 200
    assert stored.json() == body

    with TestingSession() as session:
        runs = session.scalar(select(func.count()).select_from(EntityExtractionRun))
        entities = session.scalar(select(func.count()).select_from(EntityHistory))
        relations = session.scalar(select(func.count()).select_from(RelationHistory))
    assert runs == 1
    assert entities == 2
    assert relations == 1


def test_batch_and_arbitrary_llm_responses(client: TestClient) -> None:
    response = client.post(
        "/entity-extraction/batch",
        json={
            "items": [
                {"response_id": "empty", "content": ""},
                {"response_id": "plain", "response": "No named objects here."},
                {
                    "response_id": "json",
                    "raw_response": '{"entities": [{"name": "Qwen", "type": "TECHNOLOGY"}]}',
                },
            ]
        },
    )

    assert response.status_code == 201
    results = response.json()
    assert len(results) == 3
    assert results[0]["entities"] == []
    assert results[2]["entities"][0]["canonical_name"] == "Qwen"
    assert client.get("/entity-extraction/missing").status_code == 404


def test_duplicate_response_id_is_rejected(client: TestClient) -> None:
    payload = {"response_id": "duplicate", "raw_response": "OpenAI Inc"}
    assert client.post("/entity-extraction/extract", json=payload).status_code == 201
    assert client.post("/entity-extraction/extract", json=payload).status_code == 409


def test_benchmark_pipeline() -> None:
    payload = ExtractionInput(
        response_id="benchmark",
        raw_response=(
            "Sam Altman works for OpenAI Inc in San Francisco. "
            "Contact team@example.com and visit https://example.com."
        ),
    )
    started = perf_counter()
    for _ in range(2_000):
        run_pipeline(payload, now=REGRESSION_TIME)
    duration = perf_counter() - started

    assert duration < 2.0
