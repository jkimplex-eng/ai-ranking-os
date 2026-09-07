from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.app.main  # noqa: F401 - register all mapped models
from backend.app.database import Base
from research.access import require_research_access
from research.models import Research, ResearchTask
from research.repositories import EntityNotFoundError, ResearchRepository, ResearchTaskRepository


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Research(id=1, title="First client", metadata_payload={"created_by_user_id": 10}),
                Research(id=2, title="Second client", metadata_payload={"created_by_user_id": 20}),
                Research(id=3, title="Legacy unowned", metadata_payload={}),
            ]
        )
        db.add_all(
            [
                ResearchTask(id=1, research_id=1, query="one"),
                ResearchTask(id=2, research_id=2, query="two"),
            ]
        )
        db.commit()
        yield db
    engine.dispose()


def test_client_lists_are_filtered_before_pagination(database):
    database.info["research_user_id"] = 20
    assert [item.id for item in ResearchRepository(database).list(limit=1)] == [2]
    assert [item.id for item in ResearchTaskRepository(database).list()] == [2]
    with pytest.raises(EntityNotFoundError):
        ResearchRepository(database).get(1)
    with pytest.raises(EntityNotFoundError):
        ResearchRepository(database).get(3)


@pytest.mark.parametrize("params", [{"research_id": 1}, {"task_id": 1}])
def test_foreign_details_are_hidden(database, monkeypatch, params):
    monkeypatch.setattr(
        "research.access.get_settings", lambda: SimpleNamespace(security_enforce_auth=True)
    )
    request = SimpleNamespace(
        state=SimpleNamespace(principal=SimpleNamespace(user_id=20)),
        path_params=params,
        method="GET",
        url=SimpleNamespace(path="/research/1/final-report"),
    )
    with pytest.raises(HTTPException) as error:
        require_research_access(request, database)
    assert error.value.status_code == 404


def test_owner_can_read_but_not_use_raw_mutations(database, monkeypatch):
    monkeypatch.setattr(
        "research.access.get_settings", lambda: SimpleNamespace(security_enforce_auth=True)
    )
    request = SimpleNamespace(
        state=SimpleNamespace(principal=SimpleNamespace(user_id=20)),
        path_params={"research_id": 2},
        method="GET",
        url=SimpleNamespace(path="/research/2/final-report"),
    )
    require_research_access(request, database)
    request.method = "DELETE"
    with pytest.raises(HTTPException) as error:
        require_research_access(request, database)
    assert error.value.status_code == 403
