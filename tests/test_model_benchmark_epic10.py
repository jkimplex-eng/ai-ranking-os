from collections.abc import Generator

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


def test_model_benchmark_api() -> None:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with SessionFactory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        response = client.post(
            "/providers/benchmarks",
            json={
                "prompt": "Explain AI visibility",
                "iterations": 2,
                "models": [
                    {"provider": "openai", "model": "gpt-4o-mini"},
                    {"provider": "local", "model": "local-llama"},
                ],
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert len(body["results"]) == 2
        assert all(item["stability_score"] == 1 for item in body["results"])
        assert client.get(f"/providers/benchmarks/{body['id']}").status_code == 200
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
