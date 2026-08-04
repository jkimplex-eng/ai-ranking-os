from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from entity_linking.engine import EntityLinkingEngine
from entity_linking.models import CanonicalEntity, EntityAlias, LinkDecision
from entity_linking.ports import LinkableEntity, LinkableGraph
from entity_linking.resolver import NameEntityResolver, normalize_name
from entity_linking.schemas import CandidateDecisionRequest
from graph.models import GraphNode, GraphSnapshot

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class MutableGraphProvider:
    def __init__(self, entity: LinkableEntity) -> None:
        self.entity = entity
        self.snapshot_id = 1

    def graph(self, snapshot_id: int | None = None) -> LinkableGraph:
        return LinkableGraph(snapshot_id or self.snapshot_id, (self.entity,))


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


def test_normalization_handles_case_spaces_punctuation_and_unicode() -> None:
    assert normalize_name("  ACME,   Inc.! ") == "acme inc"
    assert normalize_name("ＡＣＭＥ") == "acme"


def test_engine_creates_canonical_uses_alias_and_records_decisions(db: Session) -> None:
    provider = MutableGraphProvider(
        LinkableEntity(1, "a", "ACME", "Acme", "Brand", ("Acme, Inc.",))
    )
    engine = EntityLinkingEngine(db, provider, NameEntityResolver())
    created = engine.run()
    provider.entity = LinkableEntity(2, "b", "acme inc", "acme inc", "Brand")
    provider.snapshot_id = 2
    alias_match = engine.run()

    assert created.candidates[0].match_method == "NEW_ENTITY"
    assert alias_match.candidates[0].match_method == "EXACT_ALIAS"
    assert (
        alias_match.candidates[0].canonical_entity_id == created.candidates[0].canonical_entity_id
    )
    assert db.scalar(select(func.count(CanonicalEntity.id))) == 1
    assert db.scalar(select(func.count(EntityAlias.id))) == 1
    assert db.scalar(select(func.count(LinkDecision.id))) == 2


def test_fuzzy_candidate_supports_manual_approve_and_reject(db: Session) -> None:
    provider = MutableGraphProvider(LinkableEntity(1, "a", "OpenAI", "OpenAI", "Organization"))
    engine = EntityLinkingEngine(db, provider, NameEntityResolver())
    canonical_id = engine.run().candidates[0].canonical_entity_id

    provider.entity = LinkableEntity(2, "b", "Open AI", "Open AI", "Organization")
    pending = engine.run().candidates[0]
    approved = engine.approve(
        pending.id,
        CandidateDecisionRequest(canonical_entity_id=canonical_id, actor="reviewer"),
    )
    provider.entity = LinkableEntity(3, "c", "OpenAII", "OpenAII", "Organization")
    rejected_candidate = engine.run().candidates[0]
    rejected = engine.reject(
        rejected_candidate.id, CandidateDecisionRequest(actor="reviewer", reason="wrong")
    )

    assert pending.status == "PENDING"
    assert approved.status == "APPROVED"
    assert approved.decisions[-1].decision == "MANUAL_APPROVE"
    assert rejected.status == "REJECTED"
    assert rejected.decisions[-1].decision == "MANUAL_REJECT"


def _graph_snapshot(name: str, external_id: str) -> int:
    with TestingSession() as db:
        snapshot = GraphSnapshot(
            structure_version="1.0", node_count=1, edge_count=0, build_metadata={}
        )
        db.add(snapshot)
        db.flush()
        db.add(
            GraphNode(
                snapshot_id=snapshot.id,
                external_id=external_id,
                name=name,
                canonical_name=name,
                node_type="Organization",
                confidence=0.9,
                aliases=[],
                properties={},
            )
        )
        db.commit()
        return snapshot.id


def test_entity_linking_api_flow_and_openapi(client: TestClient) -> None:
    first_id = _graph_snapshot("OpenAI", "one")
    second_id = _graph_snapshot("Open AI", "two")
    third_id = _graph_snapshot("OpenAII", "three")
    first = client.post("/entity-linking/run", json={"snapshot_id": first_id})
    pending = client.post("/entity-linking/run", json={"snapshot_id": second_id})
    candidate_id = pending.json()["candidates"][0]["id"]
    approved = client.post(
        f"/entity-linking/{candidate_id}/approve", json={"actor": "api-reviewer"}
    )
    another = client.post("/entity-linking/run", json={"snapshot_id": third_id})
    rejected = client.post(
        f"/entity-linking/{another.json()['candidates'][0]['id']}/reject",
        json={"actor": "api-reviewer"},
    )

    assert first.status_code == 200
    assert pending.json()["pending"] == 1
    assert approved.json()["status"] == "APPROVED"
    assert rejected.json()["status"] == "REJECTED"
    assert client.get("/entity-linking/candidates", params={"status": "PENDING"}).json() == []
    assert client.post(f"/entity-linking/{candidate_id}/reject", json={}).status_code == 409
    assert client.post("/entity-linking/999/reject", json={}).status_code == 404
    paths = client.get("/openapi.json").json()["paths"]
    assert "/entity-linking/run" in paths
    assert "/entity-linking/candidates" in paths
    assert "/entity-linking/{candidate_id}/approve" in paths
    assert "/entity-linking/{candidate_id}/reject" in paths
