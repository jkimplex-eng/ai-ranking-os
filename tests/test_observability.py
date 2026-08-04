from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


def test_observability_api():
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    assert client.get("/observability/liveness").json()["status"] == "alive"
    assert client.get("/observability/readiness").json()["checks"]["database"]["healthy"]
    assert client.get("/metrics").status_code == 200
    assert "/observability/health" in app.openapi()["paths"]
    app.dependency_overrides.clear()
    engine.dispose()
