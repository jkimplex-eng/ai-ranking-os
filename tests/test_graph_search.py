from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from graph.models import GraphEdge, GraphNode, GraphSnapshot
from graph_search.engine import GraphNodeNotFoundError, GraphSearchEngine
from graph_search.ports import SearchEdge, SearchGraph, SearchNode
from graph_search.schemas import TraversalDirection

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeGraphProvider:
    def latest_graph(self) -> SearchGraph:
        return SearchGraph(
            snapshot_id=10,
            nodes=(
                SearchNode(1, "brand:acme", "ACME", "Acme", "Brand", 0.95, ("Acme Inc.",)),
                SearchNode(2, "product:one", "One", "One", "Product", 0.9),
                SearchNode(3, "source:news", "News", "News", "Source", 0.8),
                SearchNode(4, "brand:other", "Other", "Other", "Brand", 0.4),
            ),
            edges=(
                SearchEdge(1, "brand:acme", "product:one", "PRODUCES", 0.9),
                SearchEdge(2, "product:one", "source:news", "REFERENCES", 0.8),
                SearchEdge(3, "brand:other", "brand:acme", "COMPETES_WITH", 0.3),
            ),
        )


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


def test_search_supports_alias_type_relationship_filter_and_pagination() -> None:
    engine = GraphSearchEngine(FakeGraphProvider())
    alias = engine.search(query="  acme INC. ")
    filtered = engine.search(
        node_types={"product"}, relationship_types={"produces"}, min_confidence=0.5
    )
    paged = engine.search(page=2, page_size=2)

    assert [node.entity_id for node in alias.items] == ["brand:acme"]
    assert [node.entity_id for node in filtered.items] == ["product:one"]
    assert filtered.relationships[0].relationship_type == "PRODUCES"
    assert paged.total == 4
    assert len(paged.items) == 2


def test_bfs_respects_depth_direction_filters_and_shortest_distance() -> None:
    engine = GraphSearchEngine(FakeGraphProvider())
    outgoing = engine.neighbors("brand:acme", depth=2, direction=TraversalDirection.OUTGOING)
    incoming = engine.neighbors(
        "brand:acme",
        depth=1,
        direction=TraversalDirection.INCOMING,
        relationship_types={"COMPETES_WITH"},
    )

    assert [(item.node.entity_id, item.depth) for item in outgoing.items] == [
        ("product:one", 1),
        ("source:news", 2),
    ]
    assert [item.node.entity_id for item in incoming.items] == ["brand:other"]
    assert engine.get_node("1").entity_id == "brand:acme"
    with pytest.raises(GraphNodeNotFoundError):
        engine.get_node("missing")


def _seed_graph() -> None:
    with TestingSession() as db:
        snapshot = GraphSnapshot(
            structure_version="1.0", node_count=3, edge_count=2, build_metadata={}
        )
        db.add(snapshot)
        db.flush()
        nodes = [
            GraphNode(
                snapshot_id=snapshot.id,
                external_id="brand:acme",
                name="Acme",
                canonical_name="Acme",
                node_type="Brand",
                confidence=0.9,
                aliases=["ACME Inc"],
                properties={"country": "US"},
            ),
            GraphNode(
                snapshot_id=snapshot.id,
                external_id="product:one",
                name="One",
                canonical_name="One",
                node_type="Product",
                confidence=0.8,
                aliases=[],
                properties={},
            ),
            GraphNode(
                snapshot_id=snapshot.id,
                external_id="source:news",
                name="News",
                canonical_name="News",
                node_type="Source",
                confidence=0.7,
                aliases=[],
                properties={},
            ),
        ]
        db.add_all(nodes)
        db.flush()
        db.add_all(
            [
                GraphEdge(
                    snapshot_id=snapshot.id,
                    source_node_id=nodes[0].id,
                    target_node_id=nodes[1].id,
                    edge_type="PRODUCES",
                    confidence=0.9,
                    properties={},
                ),
                GraphEdge(
                    snapshot_id=snapshot.id,
                    source_node_id=nodes[1].id,
                    target_node_id=nodes[2].id,
                    edge_type="REFERENCES",
                    confidence=0.8,
                    properties={},
                ),
            ]
        )
        db.commit()


def test_graph_search_api_and_openapi(client: TestClient) -> None:
    _seed_graph()
    search = client.get("/graph/search", params={"q": "acme inc", "node_type": "Brand"})
    node = client.get("/graph/node/brand:acme")
    neighbors = client.get(
        "/graph/neighbors/brand:acme",
        params={"depth": 2, "direction": "OUTGOING", "page_size": 1},
    )

    assert search.status_code == 200
    assert search.json()["items"][0]["entity_id"] == "brand:acme"
    assert node.status_code == 200
    assert node.json()["properties"] == {"country": "US"}
    assert neighbors.status_code == 200
    assert neighbors.json()["total"] == 2
    assert len(neighbors.json()["items"]) == 1
    paths = client.get("/openapi.json").json()["paths"]
    assert "/graph/search" in paths
    assert "/graph/node/{id}" in paths
    assert "/graph/neighbors/{id}" in paths


def test_graph_search_api_validation_and_errors(client: TestClient) -> None:
    assert client.get("/graph/search").status_code == 404
    _seed_graph()
    assert client.get("/graph/node/missing").status_code == 404
    assert client.get("/graph/neighbors/brand:acme", params={"depth": 6}).status_code == 422
    assert client.get("/graph/search", params={"page_size": 101}).status_code == 422
