from collections.abc import Generator
from io import BytesIO

import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from analytics.models import AnalyticsRun
from analytics.schemas import AnalyticsFilter, FilterOperator
from backend.app.database import Base, get_db
from backend.app.main import app
from export_engine.schemas import ExportFormat, ExportRequest
from export_engine.service import ExportColumnNotFoundError, ExportService

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeRepository:
    def rows(self, analytics_run_ids: list[int]):
        rows = [
            {"run_id": 1, "entity": "Acme", "visibility": 80.0, "note": "=unsafe"},
            {"run_id": 2, "entity": "Other", "visibility": 40.0, "note": "safe"},
        ]
        return (row for row in rows if row["run_id"] in analytics_run_ids)


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


def _content(service: ExportService, request: ExportRequest) -> bytes:
    return b"".join(service.export(request).chunks)


def test_csv_and_json_stream_filter_projection_batch_and_formula_safety() -> None:
    service = ExportService(FakeRepository())
    csv_content = _content(
        service,
        ExportRequest(
            analytics_run_ids=[1, 2],
            format=ExportFormat.CSV,
            columns=["entity", "visibility", "note"],
            batch_size=1,
        ),
    ).decode("utf-8-sig")
    json_content = _content(
        service,
        ExportRequest(
            analytics_run_ids=[1, 2],
            format=ExportFormat.JSON,
            columns=["entity", "visibility"],
            filters=[AnalyticsFilter(field="visibility", operator=FilterOperator.GTE, value=50)],
        ),
    )

    assert "'=unsafe" in csv_content
    assert csv_content.count("\n") == 3
    assert json_content == b'[{"entity":"Acme","visibility":80.0}]'


def test_xlsx_and_parquet_are_real_interoperable_files() -> None:
    service = ExportService(FakeRepository())
    request = {
        "analytics_run_ids": [1, 2],
        "columns": ["run_id", "entity", "visibility"],
        "batch_size": 1,
    }
    xlsx = _content(service, ExportRequest(format=ExportFormat.XLSX, **request))
    parquet = _content(service, ExportRequest(format=ExportFormat.PARQUET, **request))

    workbook = load_workbook(BytesIO(xlsx), read_only=True)
    values = list(workbook["Analytics"].values)
    table = pq.read_table(BytesIO(parquet))
    assert values[0] == ("run_id", "entity", "visibility")
    assert values[1] == (1, "Acme", 80)
    assert table.column_names == ["run_id", "entity", "visibility"]
    assert table.num_rows == 2


def test_export_validates_requested_columns() -> None:
    with pytest.raises(ExportColumnNotFoundError):
        ExportService(FakeRepository()).export(
            ExportRequest(analytics_run_ids=[1], format=ExportFormat.JSON, columns=["missing"])
        )


def _seed_analytics_run(value: float) -> int:
    with TestingSession() as db:
        run = AnalyticsRun(
            engine_version="1.0",
            query_payload={"metrics": ["visibility"]},
            result_payload={
                "groups": [
                    {
                        "dimensions": {"entity_id": f"entity-{value}"},
                        "interval_start": None,
                        "record_count": 1,
                        "metrics": {"visibility": {"values": {"AVG": value}}},
                    }
                ]
            },
            source_record_count=1,
            group_count=1,
        )
        db.add(run)
        db.commit()
        return run.id


def test_export_api_streams_batches_handles_errors_and_updates_openapi(client: TestClient) -> None:
    first = _seed_analytics_run(80)
    second = _seed_analytics_run(40)
    response = client.post(
        "/exports",
        json={
            "analytics_run_ids": [first, second],
            "format": "CSV",
            "filename": "benchmark",
            "batch_size": 1,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="benchmark.csv"'
    assert response.headers["x-export-row-count"] == "2"
    assert "metric.visibility.avg" in response.text
    assert (
        client.post("/exports", json={"analytics_run_ids": [999], "format": "JSON"}).status_code
        == 404
    )
    assert (
        client.post(
            "/exports",
            json={"analytics_run_ids": [first], "format": "JSON", "columns": ["missing"]},
        ).status_code
        == 422
    )
    operation = client.get("/openapi.json").json()["paths"]["/exports"]["post"]
    assert "text/csv" in operation["responses"]["200"]["content"]
    assert "application/vnd.apache.parquet" in operation["responses"]["200"]["content"]
