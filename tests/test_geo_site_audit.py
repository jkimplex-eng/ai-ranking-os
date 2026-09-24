from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from geo_site_audit.schemas import SiteAuditCreate
from geo_site_audit.service import GeoSiteAuditService, PublicSiteFetcher, SiteAuditError

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
            "email":"info@brand.example"},{"@type":"Product","name":"Сыворотка",
            "sku":"SERUM-001","additionalProperty":[{"@type":"PropertyValue",
            "name":"Объём","value":"30 мл"}],
            "offers":{"@type":"Offer","availability":"https://schema.org/InStock"}},
            {"@type":"FAQPage"}]}</script></head><body>
            <h1>Brand — косметика для здоровья кожи</h1>
            <a href="/about">О компании</a>
            <a href="/sitemap.xml">Карта сайта</a>
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
    assert result.algorithm_version == "1.2"
    assert len(result.checks) == 23
    assert all(check.evidence for check in result.checks)
    assert all(check.checked_url == "https://brand.example/" for check in result.checks)
    assert all(item.checked_url == "https://brand.example/" for item in result.opportunities)
    assert result.evidence["robots_status"] == 200
    assert result.evidence["crawl_scope"]["pages_scanned"] == 1
    assert result.evidence["knowledge_graph"]["nodes"]
    assert result.evidence["page_issues"] == []
    assert result.evidence["roadmap"]["current"] == result.score
    assert "не гарантирует рекомендацию" in result.evidence["roadmap"]["condition"]

    stored = client.get("/geo/site-audits")
    assert stored.status_code == 200
    assert stored.json()[0]["brand"] == "Brand"


def test_geo_site_audit_page_issues_are_url_specific() -> None:
    issues = GeoSiteAuditService._page_issues(
        [
            {
                "url": "https://brand.example/catalog",
                "status": 200,
                "title": None,
                "h1": [],
                "json_ld_types": [],
            },
            {
                "url": "https://brand.example/about",
                "status": 200,
                "title": "О компании",
                "h1": ["О компании"],
                "json_ld_types": ["AboutPage"],
            },
            {"url": "https://brand.example/down", "status": 503, "error": "страница недоступна"},
        ]
    )
    assert issues == [{
        "url": "https://brand.example/catalog",
        "signals": [
            {"signal": "title", "action": "Добавить уникальный title на этой странице."},
            {"signal": "h1", "action": "Добавить один описательный H1 на этой странице."},
            {
                "signal": "JSON-LD",
                "action": (
                    "Добавить подтверждённую Schema.org-разметку, "
                    "соответствующую содержанию страницы."
                ),
            },
        ],
    }]


def test_geo_site_audit_flags_missing_verified_product_card_facts() -> None:
    issues = GeoSiteAuditService._page_issues(
        [{
            "url": "https://brand.example/catalog/part",
            "status": 200,
            "title": "Деталь",
            "h1": ["Деталь для автомобиля"],
            "json_ld_types": ["Product"],
            "product_facts": {
                "products": 1,
                "has_identifier": False,
                "has_availability": False,
                "has_properties": False,
            },
        }]
    )

    assert issues[0]["url"] == "https://brand.example/catalog/part"
    assert [item["signal"] for item in issues[0]["signals"]] == [
        "идентификатор товара",
        "наличие товара",
        "характеристики товара",
    ]


def test_geo_site_audit_is_documented_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/geo/site-audits" in paths
    assert "/geo/site-audits/{audit_id}" in paths


def test_public_fetcher_revalidates_every_redirect_target(monkeypatch: pytest.MonkeyPatch) -> None:
    attempted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempted.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    fetcher = PublicSiteFetcher(httpx.Client(transport=httpx.MockTransport(handler)))
    checked: list[str] = []

    def check_public(host: str) -> None:
        checked.append(host)
        if host == "127.0.0.1":
            raise SiteAuditError("Разрешён аудит только публичных сайтов")

    monkeypatch.setattr(fetcher, "_public", check_public)
    with pytest.raises(SiteAuditError, match="только публичных"):
        fetcher.fetch("https://brand.example")

    assert attempted == ["https://brand.example"]
    assert checked == ["brand.example", "127.0.0.1"]
