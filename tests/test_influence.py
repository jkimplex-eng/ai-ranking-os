from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from graph.models import GraphEdge, GraphNode, GraphSnapshot
from influence.engine import InfluenceEngine
from influence.models import EntityInfluence, InfluenceSnapshot
from influence.ports import InfluenceEdge, InfluenceGraph, InfluenceNode

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeGraphProvider:
    def latest_graph(self) -> InfluenceGraph:
        return InfluenceGraph(
            snapshot_id=7,
            nodes=(
                InfluenceNode("a", "A", "Brand"),
                InfluenceNode("b", "B", "Product"),
                InfluenceNode("c", "C", "Source"),
            ),
            edges=(
                InfluenceEdge("a", "b", 1.0),
                InfluenceEdge("b", "c", 0.5),
                InfluenceEdge("a", "c", 0.25),
            ),
        )


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


def test_engine_calculates_all_metrics_and_persists_idempotently(db: Session) -> None:
    engine = InfluenceEngine(db, FakeGraphProvider())
    first = engine.calculate()
    second = engine.calculate()

    assert first.id == second.id
    assert first.algorithm_version == "1.0"
    assert first.node_count == 3
    assert first.edge_count == 3
    assert [entity.entity_id for entity in first.entities] == ["a", "b", "c"]
    assert first.entities[0].rank == 1
    assert first.entities[0].degree == 1
    assert first.entities[0].weighted_degree == 0.3125
    assert first.entities[0].pagerank > 0
    assert first.entities[1].betweenness == 0
    assert first.entities[0].closeness == 1
    assert 0 <= first.entities[0].influence_score <= 100
    assert db.scalar(select(func.count(InfluenceSnapshot.id))) == 1
    assert db.scalar(select(func.count(EntityInfluence.id))) == 3


def test_single_node_graph_has_defined_metrics(db: Session) -> None:
    class SingleNodeProvider:
        def latest_graph(self) -> InfluenceGraph:
            return InfluenceGraph(8, (InfluenceNode("only", "Only", "Brand"),), ())

    entity = InfluenceEngine(db, SingleNodeProvider()).calculate().entities[0]
    assert entity.degree == 0
    assert entity.weighted_degree == 0
    assert entity.pagerank == 1
    assert entity.betweenness == 0
    assert entity.closeness == 0
    assert entity.influence_score == 25


def _seed_graph() -> None:
    with TestingSession() as db:
        snapshot = GraphSnapshot(
            structure_version="1.0", node_count=2, edge_count=1, build_metadata={}
        )
        db.add(snapshot)
        db.flush()
        left = GraphNode(
            snapshot_id=snapshot.id,
            external_id="brand:acme",
            name="Acme",
            canonical_name="Acme",
            node_type="Brand",
            confidence=1,
            aliases=[],
            properties={},
        )
        right = GraphNode(
            snapshot_id=snapshot.id,
            external_id="source:one",
            name="One",
            canonical_name="One",
            node_type="Source",
            confidence=1,
            aliases=[],
            properties={},
        )
        db.add_all([left, right])
        db.flush()
        db.add(
            GraphEdge(
                snapshot_id=snapshot.id,
                source_node_id=left.id,
                target_node_id=right.id,
                edge_type="REFERENCES",
                confidence=0.8,
                properties={},
            )
        )
        db.commit()


def test_influence_api_collection_entity_and_openapi(client: TestClient) -> None:
    _seed_graph()
    collection = client.get("/graph/influence")
    entity = client.get("/graph/influence/brand:acme")

    assert collection.status_code == 200
    assert collection.json()["node_count"] == 2
    assert len(collection.json()["entities"]) == 2
    assert entity.status_code == 200
    assert entity.json()["entity_id"] == "brand:acme"
    paths = client.get("/openapi.json").json()["paths"]
    assert "/graph/influence" in paths
    assert "/graph/influence/{entity_id}" in paths


def test_influence_api_errors(client: TestClient) -> None:
    assert client.get("/graph/influence").status_code == 404
    _seed_graph()
    assert client.get("/graph/influence/missing").status_code == 404
