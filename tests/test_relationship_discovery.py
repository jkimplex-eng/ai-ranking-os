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
from graph.models import GraphNode, GraphSnapshot
from relationship_discovery.engine import RelationshipDiscoveryEngine
from relationship_discovery.models import RelationshipDecision, RelationshipEvidence
from relationship_discovery.ports import (
    DiscoveryEntity,
    DiscoveryGraph,
    EvidenceItem,
    ExistingRelationship,
)
from relationship_discovery.schemas import RelationshipDecisionRequest

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeGraphProvider:
    def __init__(self) -> None:
        self.integrated: list[EvidenceItem] = []

    def graph(self, snapshot_id: int | None = None) -> DiscoveryGraph:
        return DiscoveryGraph(
            snapshot_id or 1,
            (DiscoveryEntity("a"), DiscoveryEntity("b"), DiscoveryEntity("c")),
            (ExistingRelationship("a", "c", "MENTIONS"),),
        )

    def integrate(self, snapshot_id: int, evidence: EvidenceItem) -> int:
        self.integrated.append(evidence)
        return 99


class FakeEvidenceProvider:
    def evidence(self, graph: DiscoveryGraph) -> list[EvidenceItem]:
        return [
            EvidenceItem("a", "b", "PRODUCES", 0.8, "response", "one"),
            EvidenceItem("a", "b", "PRODUCES", 0.5, "citation", "two"),
            EvidenceItem("a", "b", "PRODUCES", 0.5, "citation", "two"),
            EvidenceItem("a", "c", "MENTIONS", 1, "response", "existing"),
            EvidenceItem("missing", "b", "RELATED_TO", 1, "response", "bad"),
            EvidenceItem("b", "c", "UNSUPPORTED", 1, "response", "unsupported"),
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


def test_engine_aggregates_evidence_confidence_and_deduplicates(db: Session) -> None:
    graph = FakeGraphProvider()
    engine = RelationshipDiscoveryEngine(db, graph, FakeEvidenceProvider())
    first = engine.run()
    second = engine.run()

    assert first.candidate_count == 1
    assert first.candidates[0].confidence == 0.9
    assert len(first.candidates[0].evidence) == 2
    assert second.candidates[0].id == first.candidates[0].id
    assert db.scalar(select(func.count(RelationshipEvidence.id))) == 2


def test_manual_decisions_integrate_approved_candidate(db: Session) -> None:
    graph = FakeGraphProvider()
    engine = RelationshipDiscoveryEngine(db, graph, FakeEvidenceProvider())
    approved_candidate = engine.run().candidates[0]
    approved = engine.approve(approved_candidate.id, RelationshipDecisionRequest(actor="reviewer"))
    assert approved.status == "APPROVED"
    assert approved.integrated_snapshot_id == 99
    assert graph.integrated[0].relationship_type == "PRODUCES"
    assert approved.decisions[-1].decision == "APPROVE"
    rejected_candidate = engine.run(2).candidates[0]
    rejected = engine.reject(rejected_candidate.id, RelationshipDecisionRequest(actor="reviewer"))
    assert rejected.status == "REJECTED"
    assert rejected.decisions[-1].decision == "REJECT"
    assert db.scalar(select(func.count(RelationshipDecision.id))) == 2


def _seed_graph_and_evidence() -> int:
    with TestingSession() as db:
        snapshot = GraphSnapshot(
            structure_version="1.0", node_count=2, edge_count=0, build_metadata={}
        )
        db.add(snapshot)
        db.flush()
        db.add_all(
            [
                GraphNode(
                    snapshot_id=snapshot.id,
                    external_id="kg:a",
                    name="A",
                    canonical_name="A",
                    node_type="Brand",
                    confidence=1,
                    aliases=[],
                    properties={},
                ),
                GraphNode(
                    snapshot_id=snapshot.id,
                    external_id="kg:b",
                    name="B",
                    canonical_name="B",
                    node_type="Product",
                    confidence=1,
                    aliases=[],
                    properties={},
                ),
            ]
        )
        run = EntityExtractionRun(
            response_id="r",
            raw_response={},
            output_payload={},
            version="1.0",
            processed_at=datetime.now(UTC),
        )
        db.add(run)
        db.flush()
        db.add_all(
            [
                EntityHistory(
                    run_id=run.id,
                    response_id="r",
                    entity_id="e1",
                    name="A",
                    canonical_name="A",
                    entity_type="BRAND",
                    confidence=1,
                    aliases=[],
                    knowledge_graph_id="kg:a",
                ),
                EntityHistory(
                    run_id=run.id,
                    response_id="r",
                    entity_id="e2",
                    name="B",
                    canonical_name="B",
                    entity_type="PRODUCT",
                    confidence=1,
                    aliases=[],
                    knowledge_graph_id="kg:b",
                ),
                RelationHistory(
                    run_id=run.id,
                    response_id="r",
                    relation_id="rel-1",
                    source_entity_id="e1",
                    target_entity_id="e2",
                    relation_type="PRODUCES",
                    confidence=0.8,
                ),
            ]
        )
        db.commit()
        return snapshot.id


def test_relationship_discovery_api_and_graph_integration(client: TestClient) -> None:
    snapshot_id = _seed_graph_and_evidence()
    run = client.post("/relationship-discovery/run", json={"snapshot_id": snapshot_id})
    candidate_id = run.json()["candidates"][0]["id"]
    approved = client.post(f"/relationship-discovery/{candidate_id}/approve", json={"actor": "api"})
    derived = client.get(f"/graph/{approved.json()['integrated_snapshot_id']}")

    assert run.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert derived.json()["edge_count"] == 1
    assert derived.json()["edges"][0]["edge_type"] == "PRODUCES"
    assert client.get("/relationship-discovery/candidates").status_code == 200
    assert client.post(f"/relationship-discovery/{candidate_id}/reject", json={}).status_code == 409
    paths = client.get("/openapi.json").json()["paths"]
    assert "/relationship-discovery/run" in paths
    assert "/relationship-discovery/candidates" in paths
    assert "/relationship-discovery/{candidate_id}/approve" in paths
    assert "/relationship-discovery/{candidate_id}/reject" in paths


def test_relationship_discovery_api_errors(client: TestClient) -> None:
    assert client.post("/relationship-discovery/run", json={}).status_code == 404
    assert client.post("/relationship-discovery/999/reject", json={}).status_code == 404
