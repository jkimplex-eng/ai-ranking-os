import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from audit.repository import AuditRepository
from audit.service import AuditService
from backend.app.database import Base, get_db
from backend.app.main import app


def test_audit_immutable_and_api():
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        event = AuditService(AuditRepository(db)).record(
            actor_id="1",
            actor_type="user",
            action="login",
            category="authentication",
            resource="session",
            correlation_id="cid",
        )
        model = AuditRepository(db).search(page=1, page_size=10)[0][0]
        model.action = "changed"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
        assert event.action == "login"

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    assert client.get("/audit/events?category=authentication").json()["total"] == 1
    assert client.get("/audit/export").headers["content-type"].startswith("text/csv")
    assert "/audit/events" in app.openapi()["paths"]
    app.dependency_overrides.clear()
    engine.dispose()
