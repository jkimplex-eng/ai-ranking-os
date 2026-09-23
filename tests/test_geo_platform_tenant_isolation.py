from uuid import uuid4
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.app.main  # noqa: F401 - load ORM relationship targets
from backend.app.database import Base
from geo_platforms.models import GeoPlatform
from geo_platforms.repository import PlatformRepository
from geo_platforms.router import require_platform_scope
from geo_platforms.schemas import PlatformCreate
from geo_platforms.service import PlatformService
from organization_workspace.models import Organization
from product.source_inspection import SourceInspectionService
from research.models import Research


def test_platforms_and_publication_evidence_are_isolated_by_organization() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Organization(id=1, name="Client one", slug="client-one"),
            Organization(id=2, name="Client two", slug="client-two"),
        ])
        db.commit()
        db.info["geo_organization_id"] = 1
        repository = PlatformRepository(db)
        first = PlatformService(repository).create(
            PlatformCreate(name="Example", domain="example.ru", evidence={"query": "private one"})
        )
        assert first.organization_id == 1

        db.info["geo_organization_id"] = 2
        assert repository.list() == []
        assert repository.get(first.id) is None
        assert repository.by_domain("example.ru") is None
        second = PlatformService(repository).create(
            PlatformCreate(name="Example", domain="example.ru", evidence={"query": "private two"})
        )
        assert second.organization_id == 2
        assert [item.id for item in repository.list()] == [second.id]

        # Legacy rows with unknown ownership must not become visible to either client.
        db.add(GeoPlatform(id=uuid4(), name="Legacy", domain="legacy.ru", evidence={"query": "unknown"}))
        db.commit()
        assert [item.id for item in repository.list()] == [second.id]
        db.info["geo_organization_id"] = 1
        assert [item.id for item in repository.list()] == [first.id]
    engine.dispose()


def test_authenticated_scope_rejects_missing_principal(monkeypatch) -> None:
    monkeypatch.setattr(
        "geo_platforms.router.get_settings",
        lambda: SimpleNamespace(security_enforce_auth=True),
    )
    with pytest.raises(HTTPException) as error:
        require_platform_scope(SimpleNamespace(state=SimpleNamespace()), SimpleNamespace(info={}))
    assert error.value.status_code == 401


def test_authenticated_scope_selects_principals_organization(monkeypatch) -> None:
    monkeypatch.setattr(
        "geo_platforms.router.get_settings",
        lambda: SimpleNamespace(security_enforce_auth=True),
    )
    monkeypatch.setattr(
        "geo_platforms.router.default_organization", lambda _db, user_id: user_id + 100
    )
    db = SimpleNamespace(info={})
    require_platform_scope(
        SimpleNamespace(state=SimpleNamespace(principal=SimpleNamespace(user_id=21))), db
    )
    assert db.info["geo_organization_id"] == 121
    assert db.info["geo_user_id"] == 21


def test_observed_candidate_uses_saved_evidence_not_client_claims() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Organization(id=1, name="Client one", slug="client-one"),
            Organization(id=2, name="Client two", slug="client-two"),
        ])
        evidence = {
            "version": "yandex-generative-search-1.1",
            "status": "MEASURED",
            "source_patterns": [{
                "domain": "example.ru", "used_in_answers": 1,
                "evidence": [{
                    "query": "как выбрать крем", "url": "https://example.ru/guide", "title": "Guide",
                }],
            }],
        }
        db.add_all([
            Research(id=101, title="First", metadata_payload={
                "organization_id": 1, "product_artifacts": {"yandex_generative_evidence": evidence},
            }),
            Research(id=202, title="Second", metadata_payload={
                "organization_id": 2, "product_artifacts": {"yandex_generative_evidence": evidence},
            }),
        ])
        db.commit()
        db.info.update(geo_organization_id=1, geo_user_id=11)
        service = PlatformService(PlatformRepository(db))
        with pytest.raises(ValueError, match="saved research"):
            service.create(PlatformCreate(
                name="Fake", domain="fake.ru", source="YANDEX_SEARCH_GENERATIVE",
                evidence={"source_observations": [{"query": "fabricated"}]},
            ))
        with pytest.raises(ValueError, match="not used"):
            service.register_observed(101, "fake.ru")
        with pytest.raises(LookupError, match="Research not found"):
            service.register_observed(202, "example.ru")
        first = service.register_observed(101, "example.ru")
        assert first.organization_id == 1
        assert first.evidence["source_observations"] == [{
            "query": "как выбрать крем", "url": "https://example.ru/guide", "title": "Guide",
        }]
        assert service.register_observed(101, "example.ru").id == first.id
        db.info.update(geo_organization_id=2, geo_user_id=22)
        second = service.register_observed(202, "example.ru")
        assert second.id != first.id
        assert second.organization_id == 2
    engine.dispose()


def test_unused_yandex_source_does_not_enter_inspection() -> None:
    grouped = SourceInspectionService._group([], {
        "yandex_generative_evidence": {
            "observations": [{
                "query": "test", "sources": [
                    {"url": "https://unused.ru/article", "used": False},
                    {"url": "https://used.ru/article", "used": True},
                ],
            }],
        },
    })
    assert "unused.ru" not in grouped
    assert "used.ru" in grouped
