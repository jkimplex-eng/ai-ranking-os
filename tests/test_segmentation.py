from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from analytics.ports import AnalyticsRecord
from analytics.schemas import AnalyticsFilter, FilterOperator
from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import Research, ResearchScore, ResearchStatus, ResearchTask
from segmentation.models import SegmentEvaluation, SegmentMembership
from segmentation.repository import SqlAlchemySegmentRepository
from segmentation.schemas import SegmentCreate, SegmentType, SegmentUpdate
from segmentation.service import InactiveSegmentError, SegmentService

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeSource:
    def records(self, date_from=None, date_to=None) -> list[AnalyticsRecord]:
        return [
            AnalyticsRecord(
                datetime(2026, 1, 1, tzinfo=UTC),
                {"brand": "Acme", "country": "US", "language": "en"},
                {"visibility": 80},
            ),
            AnalyticsRecord(
                datetime(2026, 1, 2, tzinfo=UTC),
                {"brand": "Other", "country": "DE", "language": "de"},
                {"visibility": 40},
            ),
        ]


@pytest.fixture
def db() -> Generator[Session]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(test_engine)


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


def test_builtin_and_custom_segments_are_extensible_and_persist_memberships(db: Session) -> None:
    service = SegmentService(FakeSource(), SqlAlchemySegmentRepository(db))
    brand = service.create(
        SegmentCreate(
            code="acme",
            name="Acme",
            segment_type=SegmentType.BRAND,
            rules=[AnalyticsFilter(field="brand", value="Acme")],
        )
    )
    custom = service.create(
        SegmentCreate(
            code="high-us",
            name="High US",
            segment_type=SegmentType.CUSTOM,
            rules=[
                AnalyticsFilter(field="country", value="US"),
                AnalyticsFilter(field="visibility", operator=FilterOperator.GTE, value=70),
            ],
        )
    )
    first = service.evaluate(brand.id)
    second = service.evaluate(custom.id)

    assert first.source_count == 2
    assert first.matched_count == 1
    assert first.members[0].dimensions["brand"] == "Acme"
    assert second.matched_count == 1
    assert service.latest_memberships(brand.id).id == first.id
    assert db.scalar(select(func.count(SegmentEvaluation.id))) == 2
    assert db.scalar(select(func.count(SegmentMembership.id))) == 2


def test_segment_crud_pagination_and_inactive_guard(db: Session) -> None:
    service = SegmentService(FakeSource(), SqlAlchemySegmentRepository(db))
    segment = service.create(
        SegmentCreate(
            code="english",
            name="English",
            segment_type=SegmentType.LANGUAGE,
            rules=[AnalyticsFilter(field="language", value="en")],
        )
    )
    updated = service.update(segment.id, SegmentUpdate(name="English language", is_active=False))

    assert updated.name == "English language"
    assert service.list(1, 1).total == 1
    with pytest.raises(InactiveSegmentError):
        service.evaluate(segment.id)
    service.delete(segment.id)
    assert service.list(1, 20).total == 0


def _seed_platform_record() -> None:
    with TestingSession() as db:
        research = Research(
            entity_id=uuid4(),
            title="Segment source",
            status=ResearchStatus.COMPLETED,
            metadata_payload={
                "brand": "Acme",
                "category": "Beauty",
                "country": "US",
                "marketplace": "Amazon",
                "source": "Web",
                "language": "en",
            },
        )
        db.add(research)
        db.flush()
        db.add(
            ResearchTask(
                research_id=research.id,
                query="test",
                model="gpt-5",
                metadata_payload={},
            )
        )
        db.add(
            ResearchScore(
                research_id=research.id,
                mention_score=70,
                recommendation_score=60,
                citation_score=50,
                coverage_score=80,
                confidence_score=90,
                visibility_score=72,
                version="1.0",
            )
        )
        db.commit()


def test_segmentation_api_crud_evaluation_types_and_openapi(client: TestClient) -> None:
    _seed_platform_record()
    created = client.post(
        "/segments",
        json={
            "code": "us-brands",
            "name": "US brands",
            "segment_type": "COUNTRY",
            "rules": [{"field": "country", "operator": "EQ", "value": "US"}],
        },
    )
    segment_id = created.json()["id"]
    evaluated = client.post(f"/segments/{segment_id}/evaluate")

    assert created.status_code == 201
    assert evaluated.status_code == 200
    assert evaluated.json()["matched_count"] == 1
    assert evaluated.json()["members"][0]["dimensions"]["model"] == "gpt-5"
    assert client.get(f"/segments/{segment_id}/memberships").status_code == 200
    assert client.patch(f"/segments/{segment_id}", json={"version": "1.1"}).status_code == 200
    assert client.get("/segments").json()["total"] == 1
    assert len(client.get("/segments/types").json()) == 8
    paths = client.get("/openapi.json").json()["paths"]
    assert "/segments" in paths
    assert "/segments/{id}" in paths
    assert "/segments/{id}/evaluate" in paths
    assert "/segments/{id}/memberships" in paths
    assert client.delete(f"/segments/{segment_id}").status_code == 204


def test_segmentation_api_validation_conflict_and_errors(client: TestClient) -> None:
    payload = {
        "code": "invalid-brand",
        "name": "Invalid",
        "segment_type": "BRAND",
        "rules": [{"field": "country", "value": "US"}],
    }
    assert client.post("/segments", json=payload).status_code == 422
    payload["rules"] = [{"field": "brand", "value": "Acme"}]
    assert client.post("/segments", json=payload).status_code == 201
    assert client.post("/segments", json=payload).status_code == 409
    assert client.get("/segments/999").status_code == 404
    assert client.get("/segments/999/memberships").status_code == 404
