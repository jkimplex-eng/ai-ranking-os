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


def test_local_mode_never_selects_cloud_model(client: TestClient) -> None:
    response = client.post("/router/route", json={"query": "private", "routing_mode": "LOCAL"})
    assert response.status_code == 201, response.text
    assert response.json()["selected_models"] == ["local-llama"]
    assert response.json()["routing_mode"] == "LOCAL"


def test_mode_endpoint_reads_configuration(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ROUTING_MODE", "LOCAL")
    assert client.get("/router/mode").json() == {"mode": "LOCAL", "internet_required": "false"}
