from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from entity_extraction.models import EntityExtractionRun, EntityHistory, RelationHistory
from graph.engine import GraphEngine
from graph.models import GraphEdge, GraphNode, GraphSnapshot
from graph.ports import GraphBuildContext, ProvidedEntity, ProvidedRelationship

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeProvider:
    def entities(self, context: GraphBuildContext) -> list[ProvidedEntity]:
        return [
            ProvidedEntity("brand:acme", "Acme", "Acme", "Brand", 0.9),
            ProvidedEntity("product:x", "X", "X", "Product", 0.8),
            ProvidedEntity("source:one", "One", "One", "Source", 0.7),
            ProvidedEntity("brand:acme", "ACME", "Acme", "Brand", 0.5),
        ]

    def relationships(self, context: GraphBuildContext) -> list[ProvidedRelationship]:
        return [
            ProvidedRelationship("brand:acme", "product:x", "PRODUCES", 0.8),
            ProvidedRelationship("brand:acme", "product:x", "PRODUCES", 0.6),
            ProvidedRelationship("source:one", "brand:acme", "MENTIONS", 0.9),
            ProvidedRelationship("missing", "brand:acme", "RELATED_TO", 1),
        ]


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


def test_engine_builds_deduplicated_immutable_snapshots(db: Session) -> None:
    provider = FakeProvider()
    engine = GraphEngine(db, provider, provider)
    first = engine.build(GraphBuildContext(metadata={"trigger": "test"}))
    second = engine.build(GraphBuildContext())

    assert first.structure_version == "1.0"
    assert first.node_count == 3
    assert first.edge_count == 2
    assert {node.node_type for node in first.nodes} == {"Brand", "Product", "Source"}
    assert second.id != first.id
    assert db.scalar(select(func.count(GraphSnapshot.id))) == 2
    assert db.scalar(select(func.count(GraphNode.id))) == 6
    assert db.scalar(select(func.count(GraphEdge.id))) == 4
    assert engine.get(first.id).build_metadata == {"trigger": "test", "source_ids": []}


def _seed_extraction() -> None:
    with TestingSession() as db:
        run = EntityExtractionRun(
            response_id="response-1", raw_response={}, output_payload={},
            version="1.0", processed_at=datetime.now(UTC),
        )
        db.add(run)
        db.flush()
        db.add_all([
            EntityHistory(
                run_id=run.id, response_id="response-1", entity_id="e1", name="Acme",
                canonical_name="Acme", entity_type="BRAND", confidence=0.9,
                aliases=[], knowledge_graph_id="kg:acme",
            ),
            EntityHistory(
                run_id=run.id, response_id="response-1", entity_id="e2", name="Widget",
                canonical_name="Widget", entity_type="PRODUCT", confidence=0.8,
                aliases=[], knowledge_graph_id="kg:widget",
            ),
            RelationHistory(
                run_id=run.id, response_id="response-1", relation_id="r1",
                source_entity_id="e1", target_entity_id="e2",
                relation_type="PRODUCES", confidence=0.85,
            ),
        ])
        db.commit()


def test_graph_api_build_latest_get_and_openapi(client: TestClient) -> None:
    _seed_extraction()
    built = client.post("/graph/build", json={"source_ids": ["response-1"]})
    latest = client.get("/graph")
    fetched = client.get(f"/graph/{built.json()['id']}")

    assert built.status_code == 201
    assert built.json()["node_count"] == 2
    assert built.json()["edge_count"] == 1
    assert latest.json() == built.json()
    assert fetched.json() == built.json()
    paths = client.get("/openapi.json").json()["paths"]
    assert "/graph/build" in paths
    assert "/graph" in paths
    assert "/graph/{snapshot_id}" in paths


def test_graph_api_errors_and_empty_snapshot(client: TestClient) -> None:
    assert client.get("/graph").status_code == 404
    assert client.get("/graph/999").status_code == 404
    empty = client.post("/graph/build", json={})
    assert empty.status_code == 201
    assert empty.json()["nodes"] == []
    assert empty.json()["edges"] == []

