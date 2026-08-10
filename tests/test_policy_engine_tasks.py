from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine(
    "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with SessionFactory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.mark.parametrize(
    ("task_type", "policy", "strategy"),
    [
        ("entity_extraction", "latency-critical", "LOCAL_ONLY"),
        ("final_report", "quality-first", "HIGHEST_QUALITY"),
        ("embeddings", "cost-optimized", "CHEAPEST"),
        ("classification", "cost-optimized", "FREE_ONLY"),
    ],
)
def test_task_policy_resolution(
    client: TestClient, task_type: str, policy: str, strategy: str
) -> None:
    response = client.post(
        "/router/route", json={"query": "platform task", "task_type": task_type}
    )
    assert response.status_code == 201, response.text
    assert response.json()["policy_id"] == policy
    assert response.json()["strategy"] == strategy


def test_user_can_change_policy_strategy(client: TestClient) -> None:
    client.get("/router/policies")
    response = client.patch(
        "/router/policies/latency-critical", json={"strategy": "FASTEST"}
    )
    assert response.status_code == 200
    assert response.json()["strategy"] == "FASTEST"
