from collections.abc import Generator
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with testing_session() as session:
            yield session

    monkeypatch.setattr("backend.app.main.SessionLocal", testing_session)
    monkeypatch.setattr("backend.app.main.SecretCipher", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "backend.app.main.hydrate_provider_credentials", lambda *_args, **_kwargs: None
    )
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def platform_payload(domain: str = "example.com") -> dict:
    return {
        "name": "Industry Media",
        "domain": domain,
        "category": "BEAUTY",
        "country": "RU",
        "language": "ru",
        "domain_trust": 80,
        "topical_authority_score": 70,
        "ai_citation_history": 40,
        "allows_ai_crawlers": True,
        "in_knowledge_graph": True,
        "branded_mentions_90d": 600,
        "youtube_mentions": 50,
        "branded_anchors": 250,
        "branded_search_volume": 5000,
        "schema_markup_types": ["FAQPage", "Article", "Product"],
        "has_direct_answer": True,
        "content_freshness_days": 10,
        "has_structured_lists": True,
        "self_contained_paragraph_score": 90,
        "cost_per_placement": 25000,
        "evidence": {"record_ids": ["ahrefs:example.com:2026-08-14"]},
    }


def test_platform_crud_import_and_discovery(client: TestClient) -> None:
    created = client.post("/geo/platforms", json=platform_payload("https://WWW.Example.com/a"))
    assert created.status_code == 201, created.text
    platform = created.json()
    assert platform["domain"] == "example.com"

    duplicate = client.post("/geo/platforms", json=platform_payload())
    assert duplicate.status_code == 409

    imported = client.post(
        "/geo/platforms/imports",
        json={
            "provider": "ahrefs",
            "rows": [
                {"domain": "example.com", "domain_rating": 91, "brand_mentions": 750},
                {"domain": "broken"},
            ],
        },
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["rows_imported"] == 1
    assert imported.json()["rows_failed"] == 1

    discovered = client.post(
        "/geo/platforms/discover",
        json={
            "urls": [
                "https://new-media.ru/article",
                "https://www.new-media.ru/other",
                "https://example.com/source",
            ],
            "category": "BEAUTY",
            "language": "ru",
        },
    )
    assert discovered.status_code == 200, discovered.text
    assert discovered.json()["created"] == 1
    assert discovered.json()["existing"] == 1

    patched = client.patch(f"/geo/platforms/{platform['id']}", json={"topical_authority_score": 88})
    assert patched.status_code == 200
    assert patched.json()["topical_authority_score"] == 88
    assert client.delete(f"/geo/platforms/{platform['id']}").status_code == 204
    assert client.get(f"/geo/platforms/{platform['id']}").status_code == 404


def test_frozen_prompt_set_is_versioned_deterministic_and_immutable(client: TestClient) -> None:
    payload = {
        "code": "beauty-core",
        "version": 1,
        "name": "Beauty Core",
        "category": "BEAUTY",
        "language": "ru",
        "region": "RU",
        "templates": [
            {
                "key": "category",
                "query_type": "CATEGORY",
                "template": "Какую {category} выбрать для {need}?",
            },
            {
                "key": "compare",
                "query_type": "COMPARATIVE",
                "template": "{brand} или {competitor}: что лучше для {need}?",
            },
        ],
    }
    created = client.post("/geo/prompt-sets", json=payload)
    assert created.status_code == 201, created.text
    prompt_set_id = created.json()["id"]
    variables = {
        "variables": {
            "category": ["сыворотку", "крем"],
            "need": "чувствительной кожи",
            "brand": "Skinjestique",
            "competitor": "Librederm",
        }
    }
    first = client.post(f"/geo/prompt-sets/{prompt_set_id}/fan-out", json=variables)
    second = client.post(f"/geo/prompt-sets/{prompt_set_id}/fan-out", json=variables)
    assert first.status_code == second.status_code == 200
    assert first.json()["fingerprint"] == second.json()["fingerprint"]
    assert [item["text"] for item in first.json()["instances"]] == [
        item["text"] for item in second.json()["instances"]
    ]
    assert len(first.json()["instances"]) == 3
    assert client.post(f"/geo/prompt-sets/{prompt_set_id}/activate").json()["active"] is True

    version_two = {**payload, "version": 2, "name": "Beauty Core v2"}
    second_version = client.post("/geo/prompt-sets", json=version_two)
    assert second_version.status_code == 201
    client.post(f"/geo/prompt-sets/{second_version.json()['id']}/activate")
    versions = client.get("/geo/prompt-sets?code=beauty-core").json()
    assert sum(item["active"] for item in versions) == 1
    assert next(item for item in versions if item["version"] == 2)["active"] is True


def test_eis_is_reproducible_explainable_and_distinguishes_missing(client: TestClient) -> None:
    platform = client.post("/geo/platforms", json=platform_payload()).json()
    started = perf_counter()
    calculated = client.post(
        "/api/v1/eis/calculate",
        json={
            "platform_id": platform["id"],
            "ai_engine": "YandexGPT",
            "query_evidence": {
                "cep_coverage": 85,
                "semantic_similarity": 90,
                "serp_position": 2,
                "evidence_ids": ["query:1", "serp:1"],
            },
        },
    )
    assert perf_counter() - started < 2
    assert calculated.status_code == 201, calculated.text
    score = calculated.json()
    assert score["evidence_status"] == "MEASURED"
    assert score["methodology_version"] == "heuristic_v1.0"
    assert score["priority"] in {"P0", "P1", "P2", "P3"}
    explanation = score["explanation"]
    reproduced = explanation["numerator"] / explanation["denominator"]
    reproduced += explanation["engine_bias"]
    assert score["eis_value"] == pytest.approx(min(100, max(0, reproduced)), abs=0.01)
    assert explanation["engine_bias_status"] == "UNVALIDATED_PRIOR"
    assert explanation["limitation"].startswith("Correlation-based")
    assert score["signal_probabilities"] == {
        "mention": None,
        "citation": None,
        "linked": None,
        "recommendation": None,
    }
    assert client.get(f"/api/v1/eis/{score['id']}").status_code == 200

    empty = client.post(
        "/geo/platforms",
        json={"name": "Unknown", "domain": "unknown.example", "evidence": {}},
    ).json()
    not_measured = client.post(
        "/api/v1/eis/calculate",
        json={"platform_id": empty["id"], "ai_engine": "Unknown"},
    ).json()
    assert not_measured["evidence_status"] == "NOT_MEASURED"
    assert not_measured["eis_value"] is None

    measured_zero = client.post(
        "/geo/platforms",
        json={
            "name": "Measured absence",
            "domain": "measured-zero.example",
            "schema_markup_types": [],
            "evidence": {"schema_scan": "scan:zero"},
        },
    ).json()
    zero_score = client.post(
        "/api/v1/eis/calculate",
        json={
            "platform_id": measured_zero["id"],
            "ai_engine": "Unknown",
            "query_evidence": {"serp_position": 0, "evidence_ids": ["serp:not-indexed"]},
        },
    ).json()
    assert zero_score["eis_value"] == 0
    assert zero_score["components"]["content"]["inputs"]["schema_score"] == 0
    assert zero_score["components"]["match"]["inputs"]["serp_position_score"] == 0


def test_batch_prioritization_and_openapi_contract(client: TestClient) -> None:
    strong = client.post("/geo/platforms", json=platform_payload("strong.example")).json()
    weak_payload = platform_payload("weak.example")
    for key in (
        "domain_trust",
        "topical_authority_score",
        "ai_citation_history",
        "branded_mentions_90d",
        "youtube_mentions",
        "branded_anchors",
        "branded_search_volume",
        "self_contained_paragraph_score",
    ):
        weak_payload[key] = 0
    weak_payload["allows_ai_crawlers"] = False
    weak_payload["in_knowledge_graph"] = False
    weak_payload["has_direct_answer"] = False
    weak_payload["has_structured_lists"] = False
    weak_payload["schema_markup_types"] = []
    weak = client.post("/geo/platforms", json=weak_payload).json()
    response = client.post(
        "/api/v1/eis/batch-prioritize",
        json={
            "platform_ids": [weak["id"], strong["id"]],
            "ai_engine": "ChatGPT",
            "query_evidence": {
                "cep_coverage": 75,
                "semantic_similarity": 75,
                "serp_position": 5,
            },
        },
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items[0]["score"]["eis_value"] >= items[1]["score"]["eis_value"]
    paths = client.get("/openapi.json").json()["paths"]
    assert "/geo/platforms" in paths
    assert "/geo/prompt-sets/{prompt_set_id}/fan-out" in paths
    assert "/api/v1/eis/calculate" in paths
