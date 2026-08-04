from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from research.extraction import ExtractionProcessingError, ExtractionService
from research.models import Response, ResponseProcessingStatus

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


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


def _create_research_task(client: TestClient) -> int:
    research = client.post(
        "/research",
        json={"title": "Intelligence extraction"},
    ).json()
    task_response = client.post(
        "/research-tasks",
        json={
            "research_id": research["id"],
            "query": "Compare products",
            "provider": "openai",
            "model": "gpt-test",
        },
    )
    assert task_response.status_code == 201
    return task_response.json()["id"]


def test_response_is_automatically_extracted_and_available_via_api(
    client: TestClient,
) -> None:
    task_id = _create_research_task(client)
    create_response = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "openai",
            "model": "gpt-test",
            "content": "OpenAI Inc recommends ChatGPT. See https://openai.com.",
            "normalized_response": {
                "content": "OpenAI Inc recommends ChatGPT. See https://openai.com.",
                "citations": [
                    {
                        "url": "https://openai.com",
                        "title": "OpenAI",
                        "authority": 0.95,
                    }
                ],
                "finish_reason": "stop",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 8,
                    "total_tokens": 18,
                    "cost": 0.01,
                    "currency": "USD",
                },
                "metadata": {
                    "brands": ["OpenAI"],
                    "products": ["ChatGPT"],
                    "organizations": ["OpenAI Inc"],
                    "people": ["Sam Altman"],
                    "recommendations": [
                        {
                            "content": "Use ChatGPT for this workflow",
                            "confidence": 0.94,
                        }
                    ],
                },
            },
        },
    )

    assert create_response.status_code == 201
    response = create_response.json()
    assert response["processing_status"] == "PROCESSED"
    assert response["processing_error"] is None

    extraction_response = client.get(
        f"/responses/{response['id']}/extraction"
    )
    assert extraction_response.status_code == 200
    result = extraction_response.json()
    assert result["status"] == "PROCESSED"
    assert {item["name"] for item in result["brands"]} == {"OpenAI"}
    assert {item["name"] for item in result["products"]} == {"ChatGPT"}
    assert {item["name"] for item in result["organizations"]} == {"OpenAI Inc"}
    assert {item["name"] for item in result["people"]} == {"Sam Altman"}
    assert result["citations"][0]["url"] == "https://openai.com"
    assert result["citations"][0]["metadata"]["authority"] == 0.95
    assert result["recommendations"][0]["content"] == (
        "Use ChatGPT for this workflow"
    )


def test_extraction_failure_marks_response_failed(
    client: TestClient,
) -> None:
    task_id = _create_research_task(client)
    created = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "openai",
            "model": "gpt-test",
            "content": "Valid initial response",
        },
    ).json()
    with TestingSession() as db_session:
        response = db_session.get(Response, created["id"])
        assert response is not None
        response.normalized_response = {"invalid": True}
        db_session.commit()

        with pytest.raises(ExtractionProcessingError):
            ExtractionService(db_session).extract(response.id)

        db_session.refresh(response)
        assert response.processing_status == ResponseProcessingStatus.FAILED
        assert "validation" in str(response.processing_error).casefold()


def test_extraction_is_idempotent_and_openapi_is_updated(
    client: TestClient,
) -> None:
    task_id = _create_research_task(client)
    created = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "openai",
            "model": "gpt-test",
            "content": "OpenAI Inc recommends its platform.",
        },
    ).json()
    with TestingSession() as db_session:
        service = ExtractionService(db_session)
        first = service.extract(created["id"])
        second = service.extract(created["id"])

    assert len(first.entities) == len(second.entities)
    assert len(first.recommendations) == len(second.recommendations)
    assert (
        "/responses/{response_id}/extraction"
        in client.get("/openapi.json").json()["paths"]
    )
