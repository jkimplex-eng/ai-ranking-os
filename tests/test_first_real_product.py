from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from product.models import PromptDefinition, ResearchTemplateDefinition
from product.service import PIPELINE

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add(
            PromptDefinition(
                code="ai-visibility",
                version=1,
                title="AI Visibility",
                description="MVP prompt",
                category="Visibility",
                language="en",
                variables=["brand", "language", "region"],
                template="Analyze {brand} in {language} for {region}.",
                expected_output={"content": "string"},
                tags=["mvp"],
                status="ACTIVE",
                active=True,
            )
        )
        db.add(
            ResearchTemplateDefinition(
                code="ai-visibility",
                version=1,
                title="AI Visibility",
                description="Complete pipeline",
                prompt_code="ai-visibility",
                pipeline=PIPELINE,
                default_languages=["en"],
                default_regions=["GLOBAL"],
                active=True,
            )
        )
        db.commit()

    def override_get_db() -> Generator[Session]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_prompt_lifecycle_and_template_api(client: TestClient) -> None:
    prompts = client.get("/prompts")
    assert prompts.status_code == 200
    prompt_id = prompts.json()[0]["id"]

    clone = client.post(f"/prompts/{prompt_id}/clone")
    assert clone.status_code == 201
    assert clone.json()["version"] == 2
    activated = client.post(f"/prompts/{clone.json()['id']}/activate")
    assert activated.status_code == 200
    assert activated.json()["active"] is True
    deprecated = client.post(f"/prompts/{clone.json()['id']}/deprecate")
    assert deprecated.status_code == 200
    assert deprecated.json()["status"] == "DEPRECATED"

    templates = client.get("/research/templates")
    assert templates.status_code == 200
    assert templates.json()[0]["pipeline"] == PIPELINE


def test_skinjestique_end_to_end_wizard(client: TestClient) -> None:
    payload = {
        "brand": "Skinjestique",
        "models": [{"provider": "openai", "model": "gpt-4o-mini"}],
        "languages": ["en"],
        "regions": ["GLOBAL"],
        "prompt_code": "ai-visibility",
        "research_template_code": "ai-visibility",
    }
    review = client.post("/research/wizard/review", json=payload)
    assert review.status_code == 200
    assert review.json()["valid"] is True

    completed = client.post("/research/wizard/run", json=payload)
    assert completed.status_code == 201, completed.text
    body = completed.json()
    assert body["research"]["status"] == "COMPLETED", [
        item["error_message"] for item in body["report"]["responses"]
    ]
    report = body["report"]
    assert report["score"]["visibility_score"] >= 0
    assert report["detected_entities"]
    assert report["sources"]
    assert report["knowledge_graph_summary"]["node_count"] >= 1
    assert report["provider_statistics"]["openai"]["responses"] == 1
    assert report["token_usage"] > 0

    persisted = client.get(body["report_url"])
    assert persisted.status_code == 200
    assert persisted.json()["research"]["id"] == body["research"]["id"]


def test_wizard_uses_english_prompt_as_language_fallback(client: TestClient) -> None:
    response = client.post(
        "/research/wizard/review",
        json={
            "brand": "Skinjestique",
            "models": [{"provider": "anthropic", "model": "claude-3-5-sonnet"}],
            "languages": ["ru"],
            "regions": ["GLOBAL"],
            "prompt_code": "ai-visibility",
            "research_template_code": "ai-visibility",
        },
    )

    assert response.status_code == 200, response.text
    assert "Skinjestique" in response.json()["prompt"]
    assert "ru" in response.json()["prompt"]


def test_wizard_rejects_unknown_model(client: TestClient) -> None:
    response = client.post(
        "/research/wizard/review",
        json={
            "brand": "Skinjestique",
            "models": [{"provider": "openai", "model": "missing"}],
        },
    )
    assert response.status_code == 422
