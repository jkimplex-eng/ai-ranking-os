from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import Research, ResearchTask, Response
from research.repositories import (
    EntityNotFoundError,
    ResearchRepository,
    ResearchTaskRepository,
    ResponseRepository,
)
from research.schemas import (
    ResearchCreate,
    ResearchTaskCreate,
    ResearchTaskUpdate,
    ResearchUpdate,
    ResponseCreate,
    ResponseUpdate,
)

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


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


def test_repository_crud_and_relationship_filters(db: Session) -> None:
    researches = ResearchRepository(db)
    tasks = ResearchTaskRepository(db)
    responses = ResponseRepository(db)

    research = researches.create(
        ResearchCreate(
            title="AI brand visibility",
            objective="Compare global and Russian providers",
            metadata={"region": "GLOBAL"},
        )
    )
    assert research.status == "DRAFT"
    assert researches.get(research.id).metadata_payload == {"region": "GLOBAL"}

    research = researches.update(
        research.id,
        ResearchUpdate(status="ACTIVE", title="Updated research"),
    )
    assert research.status == "ACTIVE"
    assert research.title == "Updated research"

    task = tasks.create(
        ResearchTaskCreate(
            research_id=research.id,
            query="Compare OpenAI and YandexGPT",
            priority=10,
        )
    )
    task = tasks.update(
        task.id,
        ResearchTaskUpdate(
            status="COMPLETED",
            provider="openai",
            model="gpt-4o-mini",
        ),
    )
    assert tasks.list_for_research(research.id) == [task]

    response = responses.create(
        ResponseCreate(
            research_task_id=task.id,
            provider="openai",
            model="gpt-4o-mini",
            content="Result",
            prompt_tokens=11,
            completion_tokens=7,
        )
    )
    assert response.total_tokens == 18
    response = responses.update(
        response.id,
        ResponseUpdate(content="Updated", completion_tokens=9),
    )
    assert response.content == "Updated"
    assert response.total_tokens == 20
    assert responses.list_for_task(task.id) == [response]

    responses.delete(response.id)
    with pytest.raises(EntityNotFoundError):
        responses.get(response.id)
    tasks.delete(task.id)
    researches.delete(research.id)


def test_repository_rejects_missing_parents_and_cascades(db: Session) -> None:
    with pytest.raises(EntityNotFoundError):
        ResearchTaskRepository(db).create(
            ResearchTaskCreate(research_id=999, query="missing")
        )
    with pytest.raises(EntityNotFoundError):
        ResponseRepository(db).create(
            ResponseCreate(
                research_task_id=999,
                provider="openai",
                model="gpt",
                content="missing",
            )
        )

    research = ResearchRepository(db).create(ResearchCreate(title="Cascade"))
    task = ResearchTaskRepository(db).create(
        ResearchTaskCreate(research_id=research.id, query="query")
    )
    ResponseRepository(db).create(
        ResponseCreate(
            research_task_id=task.id,
            provider="openai",
            model="gpt",
            content="response",
        )
    )
    ResearchRepository(db).delete(research.id)
    assert db.scalar(select(func.count()).select_from(Research)) == 0
    assert db.scalar(select(func.count()).select_from(ResearchTask)) == 0
    assert db.scalar(select(func.count()).select_from(Response)) == 0


def test_research_api_full_crud_and_openapi(client: TestClient) -> None:
    created = client.post(
        "/researches",
        json={
            "title": "Research API",
            "description": "CRUD",
            "metadata": {"source": "test"},
        },
    )
    assert created.status_code == 201
    research_id = created.json()["id"]
    assert client.get(f"/researches/{research_id}").status_code == 200
    assert client.get("/researches").json()[0]["title"] == "Research API"
    updated = client.patch(
        f"/researches/{research_id}",
        json={"status": "ACTIVE"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "ACTIVE"

    task = client.post(
        "/research-tasks",
        json={"research_id": research_id, "query": "Run providers"},
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    assert client.get(
        "/research-tasks",
        params={"research_id": research_id},
    ).json()[0]["id"] == task_id
    assert client.patch(
        f"/research-tasks/{task_id}",
        json={"status": "RUNNING"},
    ).status_code == 200

    response = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "yandex",
            "model": "yandexgpt-pro",
            "content": "Ответ",
            "prompt_tokens": 4,
            "completion_tokens": 3,
        },
    )
    assert response.status_code == 201
    response_id = response.json()["id"]
    assert response.json()["total_tokens"] == 7
    assert client.get(f"/responses/{response_id}").status_code == 200
    assert client.patch(
        f"/responses/{response_id}",
        json={"latency_ms": 250},
    ).json()["latency_ms"] == 250
    assert client.get(
        "/responses",
        params={"research_task_id": task_id},
    ).json()[0]["id"] == response_id

    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/researches",
        "/researches/{research_id}",
        "/research-tasks",
        "/research-tasks/{task_id}",
        "/responses",
        "/responses/{response_id}",
    ):
        assert path in paths

    assert client.delete(f"/responses/{response_id}").status_code == 204
    assert client.delete(f"/research-tasks/{task_id}").status_code == 204
    assert client.delete(f"/researches/{research_id}").status_code == 204


def test_research_api_errors_and_validation(client: TestClient) -> None:
    assert client.get("/researches/999").status_code == 404
    assert client.patch("/research-tasks/999", json={"status": "FAILED"}).status_code == 404
    assert client.delete("/responses/999").status_code == 404
    assert (
        client.post(
            "/research-tasks",
            json={"research_id": 999, "query": "missing"},
        ).status_code
        == 404
    )
    invalid_tokens = client.post(
        "/responses",
        json={
            "research_task_id": 1,
            "provider": "openai",
            "model": "gpt",
            "content": "result",
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 99,
        },
    )
    assert invalid_tokens.status_code == 422
