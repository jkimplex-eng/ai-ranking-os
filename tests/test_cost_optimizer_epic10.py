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
    "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)
    with SessionFactory() as db:
        db.add(
            PromptDefinition(
                code="ai-visibility", version=1, title="AI Visibility",
                description="Prompt", category="Visibility", language="en",
                variables=["brand", "language", "region"],
                template="Analyze {brand} in {language} for {region}.",
                expected_output={}, tags=[], status="ACTIVE", active=True,
            )
        )
        db.add(
            ResearchTemplateDefinition(
                code="ai-visibility", version=1, title="AI Visibility",
                description="Pipeline", prompt_code="ai-visibility", pipeline=PIPELINE,
                default_languages=["en"], default_regions=["GLOBAL"], active=True,
            )
        )
        db.commit()
    def override() -> Generator[Session]:
        with SessionFactory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_route_estimate_contains_cost_time_models_and_budget(client: TestClient) -> None:
    response = client.post(
        "/router/estimate",
        json={"query": "research", "context_tokens": 1000, "max_output_tokens": 500},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["selected_models"]
    assert body["estimated_cost_usd"] >= 0
    assert body["estimated_time_ms"] > 0
    assert body["within_budget"] is True


def test_wizard_review_shows_estimate(client: TestClient) -> None:
    response = client.post(
        "/research/wizard/review",
        json={
            "brand": "Skinjestique",
            "models": [{"provider": "openai", "model": "gpt-4o-mini"}],
            "languages": ["en"], "regions": ["GLOBAL"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["selected_models"] == ["openai/gpt-4o-mini"]
    assert response.json()["estimated_cost_usd"] > 0
