from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from geo_site_audit.schemas import SiteAuditCreate
from geo_site_audit.service import GeoSiteAuditService

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


class _SiteFetcher:
    def fetch(self, url: str) -> tuple[str, str, int, float, str]:
        if url.endswith("robots.txt"):
            return (
                url,
                "User-agent: *\nSitemap: https://brand.example/sitemap.xml",
                200,
                12,
                "text/plain",
            )
        if url.endswith("sitemap.xml"):
            return (
                url,
                "<urlset><url><loc>https://brand.example/</loc></url></urlset>",
                200,
                12,
                "application/xml",
            )
        html = """<!doctype html><html lang="ru"><head>
            <title>Brand — экспертная косметика для ухода</title>
            <meta name="description" content="Brand создаёт экспертную косметику
            с прозрачным составом, рекомендациями специалистов и проверяемыми
            результатами для ежедневного ухода за кожей и красоты.">
            <meta name="viewport" content="width=device-width">
            <meta property="og:title" content="Brand">
            <meta property="og:description" content="Косметика Brand">
            <link rel="canonical" href="https://brand.example/">
            <script type="application/ld+json">
            {"@context":"https://schema.org","@graph":[
            {"@type":"Organization","name":"Brand","sameAs":["https://t.me/brand"],
            "email":"info@brand.example"},{"@type":"Product","name":"Сыворотка"},
            {"@type":"FAQPage"}]}</script></head><body>
            <h1>Brand — косметика для здоровья кожи</h1>
            <a href="/about">О компании</a>
            <a href="https://pubmed.ncbi.nlm.nih.gov">Исследование</a>
            <a href="https://who.int">Стандарт</a><time>2026-08-20</time>
            <span>Автор: эксперт</span></body></html>"""
        return (
            "https://brand.example/",
            html,
            200,
            120,
            "text/html; charset=utf-8",
        )


def test_geo_site_audit_is_evidence_based_and_persisted(client: TestClient) -> None:
    with TestingSession() as db:
        result = GeoSiteAuditService(db, _SiteFetcher()).run(
            1,
            SiteAuditCreate(brand="Brand", website_url="https://brand.example"),
        )

    assert result.score == 100
    assert result.algorithm_version == "1.0"
    assert len(result.checks) == 23
    assert all(check.evidence for check in result.checks)
    assert result.evidence["robots_status"] == 200

    stored = client.get("/geo/site-audits")
    assert stored.status_code == 200
    assert stored.json()[0]["brand"] == "Brand"


def test_geo_site_audit_is_documented_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/geo/site-audits" in paths
    assert "/geo/site-audits/{audit_id}" in paths
