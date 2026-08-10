from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _seed(client: TestClient) -> None:
    now = datetime.now(UTC)
    events = [
        {
            "organization_id": 7,
            "user_id": 11,
            "event_name": "LOGIN",
            "event_category": "AUTHENTICATION",
            "created_at": (now - timedelta(days=8)).isoformat(),
        },
        {
            "organization_id": 7,
            "user_id": 11,
            "event_name": "CREATE_RESEARCH",
            "event_category": "RESEARCH",
            "metadata": {"template": "geo-audit", "region": "RU", "language": "ru"},
            "created_at": (now - timedelta(hours=3)).isoformat(),
        },
        {
            "organization_id": 7,
            "user_id": 11,
            "event_name": "FINISH_RESEARCH",
            "event_category": "RESEARCH",
            "metadata": {
                "success": True,
                "status": "COMPLETED",
                "duration_ms": 4200,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "project_id": 71,
                "routing_profile": "BALANCED",
                "tokens": 900,
                "cost": 0.12,
                "latency_ms": 850,
                "visibility_score": 82,
                "recommendation_count": 4,
            },
            "created_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "organization_id": 8,
            "user_id": 12,
            "event_name": "FINISH_RESEARCH",
            "event_category": "RESEARCH",
            "metadata": {
                "success": False,
                "status": "FAILED",
                "provider": "ollama",
                "is_local": True,
                "duration_ms": 1500,
            },
            "created_at": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "organization_id": 7,
            "user_id": 11,
            "event_name": "OPEN_REPORT",
            "event_category": "REPORT",
            "entity_type": "report",
            "entity_id": "42",
            "metadata": {"generation_ms": 320},
            "created_at": now.isoformat(),
        },
        {
            "organization_id": 7,
            "user_id": 11,
            "event_name": "SUBMIT_FEEDBACK",
            "event_category": "FEEDBACK",
            "created_at": now.isoformat(),
        },
        {
            "organization_id": 7,
            "user_id": 11,
            "event_name": "PROVIDER_TIMEOUT",
            "event_category": "ERROR",
            "created_at": now.isoformat(),
        },
    ]
    response = client.post("/product-analytics/events/batch", json={"events": events})
    assert response.status_code == 201


def test_dashboard_aggregates_filters_and_cache(client: TestClient) -> None:
    _seed(client)
    response = client.get("/product-analytics/dashboard?period=DAILY")
    assert response.status_code == 200
    payload = response.json()
    assert payload["users"]["dau"] == 2
    assert payload["users"]["retention_percent"] == 100
    assert payload["research"]["success_rate"] == 50
    assert payload["research"]["failure_rate"] == 50
    assert payload["providers"]["average_tokens"] == 900
    assert payload["providers"]["paid_tokens"] == 900
    assert payload["providers"]["cost_by_model"][0]["key"] == "gpt-4o-mini"
    assert payload["organizations"]["cost"][0]["cost"] == 0.12
    assert payload["feedback"]["count"] == 1
    assert payload["errors"]["count"] == 1
    assert client.get("/product-analytics/dashboard?period=DAILY").json()["cached"] is True

    filtered = client.get("/product-analytics/dashboard?provider=openai").json()
    assert filtered["research"]["completed"] == 1
    assert filtered["providers"]["usage"][0]["key"] == "openai"


def test_sessions_pagination_exports_and_openapi(client: TestClient) -> None:
    _seed(client)
    started = client.post(
        "/product-analytics/sessions",
        json={"organization_id": 7, "device": "desktop", "browser": "Chrome", "os": "Windows"},
    )
    assert started.status_code == 201
    finished = client.post(
        f"/product-analytics/sessions/{started.json()['id']}/finish"
    )
    assert finished.status_code == 200
    assert finished.json()["duration"] >= 0
    assert len(client.get("/product-analytics/events?offset=1&limit=2").json()) == 2

    csv_response = client.get("/product-analytics/export/csv")
    assert csv_response.status_code == 200
    assert csv_response.content.startswith(b"\xef\xbb\xbfsection")
    json_response = client.get("/product-analytics/export/json")
    assert json_response.status_code == 200
    assert "overview" in json_response.json()
    xlsx_response = client.get("/product-analytics/export/xlsx")
    workbook = load_workbook(BytesIO(xlsx_response.content), read_only=True)
    assert workbook.active.title == "Product Analytics"

    paths = client.get("/openapi.json").json()["paths"]
    assert "/product-analytics/dashboard" in paths
    assert "/product-analytics/export/{format_name}" in paths
