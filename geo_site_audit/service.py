from __future__ import annotations

import ipaddress
import json
import socket
import time
from collections import defaultdict
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from sqlalchemy.orm import Session

from geo_site_audit.models import GeoSiteAudit
from geo_site_audit.repository import GeoSiteAuditRepository
from geo_site_audit.schemas import AuditCheck, AuditOpportunity, SiteAuditCreate, SiteAuditRead
from workspace.repository import ProjectRepository, WorkspaceRepository


class SiteAuditError(ValueError):
    pass


class SiteFetcher(Protocol):
    def fetch(self, url: str) -> tuple[str, str, int, float, str]: ...


class PublicSiteFetcher:
    def fetch(self, url: str) -> tuple[str, str, int, float, str]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SiteAuditError("Укажите публичный URL с http:// или https://")
        self._public(parsed.hostname)
        started = time.perf_counter()
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "AI-Ranking-OS-GEO-Audit/1.0"},
        ) as client:
            response = client.get(url)
        elapsed = (time.perf_counter() - started) * 1000
        final = urlparse(str(response.url))
        if not final.hostname:
            raise SiteAuditError("Сайт вернул некорректный URL")
        self._public(final.hostname)
        body = response.content[:2_000_000].decode(response.encoding or "utf-8", "replace")
        return (
            str(response.url),
            body,
            response.status_code,
            elapsed,
            response.headers.get("content-type", ""),
        )

    @staticmethod
    def _public(host: str) -> None:
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
        except socket.gaierror as error:
            raise SiteAuditError("Домен не найден") from error
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise SiteAuditError("Разрешён аудит только публичных сайтов")


class _AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self.h1: list[str] = []
        self.links: list[str] = []
        self.json_ld: list[dict] = []
        self.meta: dict[str, str] = {}
        self.html_lang = ""
        self._tag = ""
        self._json = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self._tag = tag
        if tag == "html":
            self.html_lang = values.get("lang") or ""
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "meta":
            key = (values.get("name") or values.get("property") or "").casefold()
            self.meta[key] = values.get("content") or ""
            if key == "description":
                self.description = values.get("content") or ""
        if tag == "script" and "ld+json" in (values.get("type") or "").casefold():
            self._json = True
            self._chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json:
            try:
                value = json.loads("".join(self._chunks))
                self.json_ld.extend(value if isinstance(value, list) else [value])
            except (json.JSONDecodeError, TypeError):
                pass
            self._json = False
        self._tag = ""

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if self._json:
            self._chunks.append(data)
        elif self._tag == "title":
            self.title += value
        elif self._tag == "h1" and value:
            self.h1.append(value)


class GeoSiteAuditService:
    VERSION = "1.1"
    MAX_CRAWLED_PAGES = 40
    LIMITATION = (
        "Оценка измеряет публичные GEO-сигналы сайта. Она не доказывает индексацию "
        "или причинное влияние на закрытые алгоритмы AI-платформ."
    )

    def __init__(self, db: Session, fetcher: SiteFetcher | None = None) -> None:
        self.db = db
        self.fetcher = fetcher or PublicSiteFetcher()
        self.repository = GeoSiteAuditRepository(db)

    def run(self, user_id: int, payload: SiteAuditCreate) -> SiteAuditRead:
        if payload.project_id is not None:
            workspace = WorkspaceRepository(self.db).get_or_create(user_id)
            ProjectRepository(self.db).get(workspace.id, payload.project_id)
        root = str(payload.website_url)
        final, html, status, latency, content_type = self.fetcher.fetch(root)
        if status >= 400 or "html" not in content_type.casefold():
            raise SiteAuditError(f"Главная страница недоступна для анализа: HTTP {status}")
        parser = _AuditParser()
        parser.feed(html)
        origin = f"{urlparse(final).scheme}://{urlparse(final).netloc}"
        robots = self._optional(f"{origin}/robots.txt")
        sitemap_url = self._sitemap_url(origin, robots[1])
        sitemap = self._optional(sitemap_url)
        pages, graph = self._crawl_public_pages(final, parser, sitemap[1])
        checks = self._checks(payload.brand, final, parser, html, status, latency, robots, sitemap)
        scores: defaultdict[str, float] = defaultdict(float)
        for check in checks:
            scores[check.category] += check.points
        score = round(sum(item.points for item in checks), 1)
        audit = GeoSiteAudit(
            user_id=user_id,
            project_id=payload.project_id,
            brand=payload.brand.strip(),
            website_url=root,
            final_url=final,
            score=score,
            grade=self._grade(score),
            category_scores=dict(scores),
            checks=[item.model_dump() for item in checks],
            opportunities=[item.model_dump() for item in self._opportunities(checks)],
            evidence={
                "http_status": status,
                "response_time_ms": round(latency, 1),
                "robots_url": f"{origin}/robots.txt",
                "robots_status": robots[0],
                "sitemap_url": sitemap_url,
                "sitemap_status": sitemap[0],
                "json_ld_types": sorted(self._types(parser.json_ld)),
                "crawl_scope": {
                    "strategy": "главная страница, sitemap и внутренние ссылки того же хоста",
                    "max_pages": self.MAX_CRAWLED_PAGES,
                    "pages_discovered": len(pages),
                    "pages_scanned": sum(item["status"] == 200 for item in pages),
                    "pages": pages,
                },
                "knowledge_graph": graph,
            },
            algorithm_version=self.VERSION,
            limitation=self.LIMITATION,
        )
        return self._read(self.repository.add(audit))

    def get(self, user_id: int, audit_id: int) -> SiteAuditRead:
        item = self.repository.get(user_id, audit_id)
        if item is None:
            raise SiteAuditError("GEO-аудит не найден")
        return self._read(item)

    def list(self, user_id: int, project_id: int | None, limit: int) -> list[SiteAuditRead]:
        return [self._read(item) for item in self.repository.list(user_id, project_id, limit)]

    def _optional(self, url: str) -> tuple[int, str]:
        try:
            _, body, status, _, _ = self.fetcher.fetch(url)
            return status, body
        except (SiteAuditError, httpx.HTTPError):
            return 0, ""

    def _crawl_public_pages(
        self,
        root_url: str,
        root_page: _AuditParser,
        sitemap: str,
    ) -> tuple[list[dict], dict]:
        """Build a bounded, same-host evidence map; it is not a claim of full indexing."""
        root = urlparse(root_url)
        candidates = [root_url]
        candidates.extend(self._sitemap_urls(sitemap, root))
        candidates.extend(urljoin(root_url, link) for link in root_page.links)

        accepted: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            parsed = urlparse(candidate)
            normalized = parsed._replace(fragment="").geturl()
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname != root.hostname
                or normalized in seen
            ):
                continue
            seen.add(normalized)
            accepted.append(normalized)
            if len(accepted) >= self.MAX_CRAWLED_PAGES:
                break

        pages: list[dict] = []
        parsed_pages: dict[str, _AuditParser] = {root_url: root_page}
        for candidate in accepted:
            if candidate == root_url:
                page = root_page
                status = 200
                content_type = "text/html"
            else:
                try:
                    final, body, status, _, content_type = self.fetcher.fetch(candidate)
                except (SiteAuditError, httpx.HTTPError):
                    pages.append({"url": candidate, "status": 0, "error": "страница недоступна"})
                    continue
                if (
                    urlparse(final).hostname != root.hostname
                    or "html" not in content_type.casefold()
                ):
                    pages.append(
                        {"url": candidate, "status": status, "error": "не HTML того же сайта"}
                    )
                    continue
                if final in parsed_pages:
                    continue
                page = _AuditParser()
                page.feed(body)
                parsed_pages[final] = page
                candidate = final
            pages.append(
                {
                    "url": candidate,
                    "status": status,
                    "title": page.title or None,
                    "h1": page.h1[:2],
                    "json_ld_types": sorted(self._types(page.json_ld)),
                    "internal_links": sum(
                        urlparse(urljoin(candidate, link)).hostname == root.hostname
                        for link in page.links
                    ),
                }
            )
        return pages, self._site_graph(parsed_pages, root.hostname or "")

    @staticmethod
    def _sitemap_urls(sitemap: str, root: object) -> list[str]:
        if not sitemap or not hasattr(root, "hostname"):
            return []
        try:
            document = ElementTree.fromstring(sitemap)
        except ElementTree.ParseError:
            return []
        urls = [item.text.strip() for item in document.findall(".//{*}loc") if item.text]
        return [
            item
            for item in urls
            if urlparse(item).scheme in {"http", "https"}
            and urlparse(item).hostname == getattr(root, "hostname", None)
        ]

    def _site_graph(self, pages: dict[str, _AuditParser], hostname: str) -> dict:
        nodes: list[dict] = []
        edges: list[dict] = []
        for url, page in pages.items():
            nodes.append({"id": url, "type": "WebPage", "label": page.title or url})
            for schema_type in sorted(self._types(page.json_ld)):
                schema_id = f"{url}#{schema_type}"
                nodes.append({"id": schema_id, "type": schema_type, "label": schema_type})
                edges.append({"from": url, "to": schema_id, "relation": "DESCRIBES"})
            for link in page.links:
                target = urljoin(url, link).split("#", 1)[0]
                target_host = urlparse(target).hostname
                if target_host == hostname:
                    edges.append({"from": url, "to": target, "relation": "LINKS_TO"})
                elif target_host:
                    edges.append({"from": url, "to": target, "relation": "CITES"})
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _sitemap_url(origin: str, robots: str) -> str:
        for line in robots.splitlines():
            if line.casefold().startswith("sitemap:"):
                return line.split(":", 1)[1].strip()
        return f"{origin}/sitemap.xml"

    def _checks(
        self,
        brand: str,
        final: str,
        page: _AuditParser,
        html: str,
        status: int,
        latency: float,
        robots: tuple[int, str],
        sitemap: tuple[int, str],
    ) -> list[AuditCheck]:
        lowered = html.casefold()
        types = self._types(page.json_ld)
        absolute_links = [urljoin(final, value) for value in page.links]
        external = {
            urlparse(value).hostname
            for value in absolute_links
            if urlparse(value).hostname and urlparse(value).hostname != urlparse(final).hostname
        }
        same_as = any(bool(node.get("sameAs")) for node in self._nodes(page.json_ld))
        facts = [
            (
                "crawl_https",
                "Доступность",
                "HTTPS",
                final.startswith("https://"),
                4,
                final,
                "Перевести сайт на HTTPS.",
            ),
            (
                "crawl_robots",
                "Доступность",
                "robots.txt доступен",
                robots[0] == 200 and "disallow: /" not in robots[1].casefold(),
                4,
                f"HTTP {robots[0] or 'нет ответа'}",
                "Открыть важные разделы для краулеров и проверить robots.txt.",
            ),
            (
                "crawl_sitemap",
                "Доступность",
                "Sitemap доступен",
                sitemap[0] == 200 and "<url" in sitemap[1].casefold(),
                4,
                f"HTTP {sitemap[0] or 'нет ответа'}",
                "Создать актуальный sitemap.xml и указать его в robots.txt.",
            ),
            (
                "crawl_index",
                "Доступность",
                "Индексация не запрещена",
                "noindex" not in page.meta.get("robots", "").casefold(),
                4,
                page.meta.get("robots", "директива отсутствует"),
                "Убрать noindex с публичных страниц.",
            ),
            (
                "crawl_canonical",
                "Доступность",
                "Канонический URL",
                'rel="canonical"' in lowered or "rel='canonical'" in lowered,
                4,
                final,
                "Добавить canonical на индексируемые страницы.",
            ),
            (
                "entity_schema",
                "Сущность",
                "Разметка организации",
                bool(types & {"Organization", "LocalBusiness", "Corporation", "Brand"}),
                8,
                ", ".join(sorted(types)) or "JSON-LD не найден",
                "Добавить Organization/Brand JSON-LD с официальными реквизитами.",
            ),
            (
                "entity_sameas",
                "Сущность",
                "Связи sameAs",
                same_as,
                4,
                "sameAs найден" if same_as else "sameAs отсутствует",
                "Связать официальный сайт с подтверждёнными профилями через sameAs.",
            ),
            (
                "entity_contacts",
                "Сущность",
                "Контактные данные",
                any(
                    token in lowered for token in ("telephone", "email", "contactpoint", "address")
                ),
                4,
                "контактные признаки в HTML/JSON-LD",
                "Опубликовать контакты и ContactPoint/PostalAddress в JSON-LD.",
            ),
            (
                "entity_brand",
                "Сущность",
                "Бренд в title/H1",
                brand.casefold() in f"{page.title} {' '.join(page.h1)}".casefold(),
                4,
                f"title: {page.title}; H1: {', '.join(page.h1)}",
                "Явно указать бренд в title и главном H1.",
            ),
            (
                "content_title",
                "Контент",
                "Содержательный title",
                20 <= len(page.title) <= 70,
                5,
                page.title or "отсутствует",
                "Сформулировать уникальный title длиной 20–70 символов.",
            ),
            (
                "content_description",
                "Контент",
                "Meta description",
                70 <= len(page.description) <= 180,
                5,
                page.description or "отсутствует",
                "Добавить конкретный meta description с категорией и ценностью бренда.",
            ),
            (
                "content_h1",
                "Контент",
                "Один понятный H1",
                len(page.h1) == 1 and len(page.h1[0]) >= 10,
                5,
                ", ".join(page.h1) or "отсутствует",
                "Оставить один описательный H1.",
            ),
            (
                "content_faq",
                "Контент",
                "FAQ для вопросов покупателей",
                "FAQPage" in types,
                5,
                "FAQPage" if "FAQPage" in types else "не найден",
                "Добавить полезный FAQ с проверяемыми ответами и FAQPage-разметкой.",
            ),
            (
                "content_offer",
                "Контент",
                "Товары или услуги структурированы",
                bool(types & {"Product", "Service", "Offer"}),
                5,
                ", ".join(sorted(types & {"Product", "Service", "Offer"})) or "не найдено",
                "Разметить Product/Service, свойства, цены и наличие.",
            ),
            (
                "evidence_author",
                "Доказательность",
                "Авторство",
                any(token in lowered for token in ("author", "автор", "reviewedby")),
                5,
                "признак авторства"
                if any(token in lowered for token in ("author", "автор", "reviewedby"))
                else "не найден",
                "Указывать автора, экспертизу и редакционную проверку.",
            ),
            (
                "evidence_dates",
                "Доказательность",
                "Даты публикации/обновления",
                any(token in lowered for token in ("datepublished", "datemodified", "<time")),
                5,
                "даты найдены"
                if any(token in lowered for token in ("datepublished", "datemodified", "<time"))
                else "не найдены",
                "Показывать дату публикации и обновления материалов.",
            ),
            (
                "evidence_sources",
                "Доказательность",
                "Внешние подтверждения",
                len(external) >= 2,
                5,
                f"внешних доменов: {len(external)}",
                "Ссылаться на первичные исследования, стандарты и независимые источники.",
            ),
            (
                "evidence_about",
                "Доказательность",
                "Страницы о компании и контактов",
                any(
                    token in value.casefold()
                    for value in absolute_links
                    for token in ("about", "contact", "о-komp", "kontakty", "about-us")
                ),
                5,
                "ссылка найдена"
                if any(
                    token in value.casefold()
                    for value in absolute_links
                    for token in ("about", "contact", "о-komp", "kontakty", "about-us")
                )
                else "не найдена",
                "Создать подробные страницы «О компании» и «Контакты».",
            ),
            (
                "tech_status",
                "Техника",
                "Главная отвечает 200",
                status == 200,
                4,
                f"HTTP {status}",
                "Исправить HTTP-ошибки и цепочки редиректов.",
            ),
            (
                "tech_latency",
                "Техника",
                "Быстрый ответ сервера",
                latency <= 1500,
                4,
                f"{latency:.0f} ms",
                "Снизить серверное время ответа до 1,5 секунды.",
            ),
            (
                "tech_viewport",
                "Техника",
                "Мобильный viewport",
                "viewport" in page.meta,
                3,
                page.meta.get("viewport", "не найден"),
                "Добавить корректный viewport и проверить мобильную версию.",
            ),
            (
                "tech_language",
                "Техника",
                "Язык документа указан",
                bool(page.html_lang),
                2,
                page.html_lang or "не указан",
                "Указать lang у элемента html.",
            ),
            (
                "tech_social",
                "Техника",
                "Open Graph",
                bool(page.meta.get("og:title") and page.meta.get("og:description")),
                2,
                "Open Graph заполнен" if page.meta.get("og:title") else "неполный",
                "Заполнить og:title, og:description и og:image.",
            ),
        ]
        return [
            AuditCheck(
                code=code,
                category=category,
                title=title,
                passed=passed,
                points=max_points if passed else 0,
                max_points=max_points,
                evidence=evidence,
                recommendation=None if passed else recommendation,
            )
            for code, category, title, passed, max_points, evidence, recommendation in facts
        ]

    @staticmethod
    def _nodes(values: list[dict]) -> list[dict]:
        result = []
        for value in values:
            if not isinstance(value, dict):
                continue
            graph = value.get("@graph")
            result.extend(item for item in graph if isinstance(item, dict)) if isinstance(
                graph, list
            ) else result.append(value)
        return result

    @classmethod
    def _types(cls, values: list[dict]) -> set[str]:
        result: set[str] = set()
        for node in cls._nodes(values):
            value = node.get("@type", [])
            result.update(
                [value] if isinstance(value, str) else value if isinstance(value, list) else []
            )
        return result

    @staticmethod
    def _grade(score: float) -> str:
        return (
            "Отличная готовность"
            if score >= 85
            else "Хорошая готовность"
            if score >= 70
            else "Требует улучшений"
            if score >= 45
            else "Критические пробелы"
        )

    @staticmethod
    def _opportunities(checks: list[AuditCheck]) -> list[AuditOpportunity]:
        failed = sorted(
            (item for item in checks if not item.passed), key=lambda item: -item.max_points
        )
        return [
            AuditOpportunity(
                priority="P0" if item.max_points >= 8 else "P1" if item.max_points >= 5 else "P2",
                problem=item.title,
                affected_metric=item.category,
                action=item.recommendation or "Исправить проверку",
                expected_effect=(
                    f"до +{item.max_points:.0f} баллов готовности GEO после повторной проверки"
                ),
                confidence="Высокая" if item.evidence else "Средняя",
                effort="Средняя" if item.max_points >= 5 else "Низкая",
                verification=f"Повторить проверку {item.code} и подтвердить URL-доказательство",
            )
            for item in failed[:10]
        ]

    @staticmethod
    def _read(item: GeoSiteAudit) -> SiteAuditRead:
        return SiteAuditRead.model_validate(item, from_attributes=True)
