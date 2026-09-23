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
