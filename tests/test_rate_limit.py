from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from rate_limit.backend import MemoryRateLimitBackend


def test_algorithms():
    b = MemoryRateLimitBackend()
    assert b.token_bucket("a", 1, 10, now=0).allowed
    denied = b.token_bucket("a", 1, 10, now=0)
    assert not denied.allowed and denied.retry_after_seconds == 10
    assert b.sliding_window("b", 1, 10, now=0).allowed
    assert not b.sliding_window("b", 1, 10, now=1).allowed
    assert b.sliding_window("b", 1, 10, now=11).allowed


def test_rate_limit_api():
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
    p = client.post(
        "/rate-limits/policies",
        json={
            "name": "ip",
            "algorithm": "sliding_window",
            "subject_type": "ip",
            "limit": 1,
            "window_seconds": 60,
        },
    ).json()
    assert (
        client.post(
            "/rate-limits/check", json={"policy_id": p["id"], "subject": "127.0.0.1"}
        ).status_code
        == 200
    )
    denied = client.post("/rate-limits/check", json={"policy_id": p["id"], "subject": "127.0.0.1"})
    assert denied.status_code == 429 and "retry-after" in denied.headers
    assert "/rate-limits/check" in app.openapi()["paths"]
    app.dependency_overrides.clear()
    engine.dispose()
