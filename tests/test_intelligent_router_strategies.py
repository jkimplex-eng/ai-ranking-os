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
    ("strategy", "expected"),
    [
        ("FASTEST", "local-llama"),
        ("CHEAPEST", "local-llama"),
        ("LOCAL_ONLY", "local-llama"),
        ("FREE_ONLY", "local-llama"),
        ("HIGHEST_QUALITY", "claude-3-5-sonnet"),
    ],
)
def test_router_strategy_selection(client: TestClient, strategy: str, expected: str) -> None:
    response = client.post(
        "/router/route",
        json={"query": "general analysis", "strategy": strategy, "language": "en"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["selected_models"][0] == expected
    assert response.json()["strategy"] == strategy
