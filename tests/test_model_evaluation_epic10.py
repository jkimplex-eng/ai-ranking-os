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


def test_evaluation_builds_capability_matrix() -> None:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with SessionFactory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        result = client.post(
            "/providers/evaluations",
            json={
                "models": [{"provider": "openai", "model": "gpt-4o-mini"}],
            },
        )
        assert result.status_code == 201, result.text
        assert len(result.json()) == 6
        matrix = client.get("/providers/capability-matrix")
        assert matrix.status_code == 200
        assert set(matrix.json()["models"]["openai/gpt-4o-mini"]) == {
            "entity_extraction",
            "intent",
            "summarization",
            "knowledge_graph",
            "recommendation",
            "report",
        }
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
