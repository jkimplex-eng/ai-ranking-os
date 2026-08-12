from __future__ import annotations

import ipaddress
import json
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx


class BrandDiscoveryError(ValueError):
    pass


class PageFetcher(Protocol):
    def fetch(self, url: str) -> tuple[str, str]: ...


class PublicHttpPageFetcher:
    """Fetch public HTTP pages with SSRF and response-size protection."""

    def fetch(self, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise BrandDiscoveryError("Укажите публичный URL сайта с http:// или https://")
        self._assert_public_host(parsed.hostname)
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "AI-Ranking-OS-Brand-Research/1.0"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            final = urlparse(str(response.url))
            if not final.hostname:
                raise BrandDiscoveryError("Сайт вернул некорректный адрес")
            self._assert_public_host(final.hostname)
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.casefold():
                raise BrandDiscoveryError("Страница сайта не содержит HTML")
            body = response.content[:2_000_000].decode(response.encoding or "utf-8", "replace")
            return str(response.url), body

    @staticmethod
    def _assert_public_host(host: str) -> None:
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
        except socket.gaierror as error:
            raise BrandDiscoveryError("Домен сайта не найден") from error
        if not addresses:
            raise BrandDiscoveryError("Домен сайта не найден")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise BrandDiscoveryError("Разрешено анализировать только публичные сайты")


@dataclass
class ParsedPage:
    url: str
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    json_ld: list[dict[str, Any]] = field(default_factory=list)


class _BrandHtmlParser(HTMLParser):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.page = ParsedPage(url=url)
        self._tag = ""
        self._json_ld = False
        self._json_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag = tag
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.page.links.append(urljoin(self.page.url, values["href"] or ""))
        if tag == "meta" and values.get("name", "").casefold() == "description":
            self.page.description = (values.get("content") or "").strip()
        if tag == "script" and "ld+json" in values.get("type", "").casefold():
            self._json_ld = True
            self._json_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json_ld:
            try:
                value = json.loads("".join(self._json_chunks))
                items = value if isinstance(value, list) else [value]
                self.page.json_ld.extend(item for item in items if isinstance(item, dict))
            except json.JSONDecodeError:
                pass
            self._json_ld = False
        self._tag = ""

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self._json_ld:
            self._json_chunks.append(data)
        elif self._tag == "title":
            self.page.title += value
        elif self._tag in {"h1", "h2", "h3"}:
            self.page.headings.append(value)
        elif self._tag not in {"script", "style", "noscript"}:
            self.page.text.append(value)


class BrandIntelligenceEngine:
    VERSION = "1.0"
    PRODUCT_HINTS = (
        "product",
        "catalog",
        "shop",
        "collection",
        "serum",
        "cream",
        "сывор",
        "крем",
        "каталог",
    )

    def __init__(self, fetcher: PageFetcher | None = None, *, max_pages: int = 12) -> None:
        self.fetcher = fetcher or PublicHttpPageFetcher()
        self.max_pages = max_pages

    def analyze(self, *, brand: str, website_url: str) -> dict[str, Any]:
        root_url = self._normalize_url(website_url)
        root_host = urlparse(root_url).hostname
        queue = [root_url]
        visited: set[str] = set()
        pages: list[ParsedPage] = []
        while queue and len(pages) < self.max_pages:
            requested = queue.pop(0)
            if requested in visited:
                continue
            visited.add(requested)
            try:
                final_url, html = self.fetcher.fetch(requested)
            except (BrandDiscoveryError, httpx.HTTPError) as error:
                if not pages:
                    raise BrandDiscoveryError(
                        "Не удалось прочитать официальный сайт бренда"
                    ) from error
                continue
            parser = _BrandHtmlParser(final_url)
            parser.feed(html)
            pages.append(parser.page)
            candidates = [
                link.split("#", 1)[0]
                for link in parser.page.links
                if urlparse(link).hostname == root_host
                and any(hint in link.casefold() for hint in self.PRODUCT_HINTS)
            ]
            queue.extend(link for link in candidates if link not in visited and link not in queue)

        products = self._products(pages)
        categories = self._categories(pages, products)
        attributes = self._attributes(pages, products)
        return {
            "version": self.VERSION,
            "brand": brand.strip(),
            "website_url": root_url,
            "pages_analyzed": len(pages),
            "evidence_urls": [page.url for page in pages],
            "description": next((page.description for page in pages if page.description), ""),
            "categories": categories[:12],
            "products": products[:30],
            "attributes": attributes[:20],
            "confidence": round(min(0.95, 0.35 + len(pages) * 0.04 + len(products) * 0.03), 2),
            "limitations": [
                "Профиль построен только по публичным страницам официального сайта.",
                "Цена и характеристики отсутствуют, если сайт не публикует их в HTML или JSON-LD.",
            ],
        }

    @staticmethod
    def _normalize_url(value: str) -> str:
        value = value.strip()
        if not value:
            raise BrandDiscoveryError("Официальный сайт обязателен для исследования")
        if "://" not in value:
            value = f"https://{value}"
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise BrandDiscoveryError("Укажите корректный URL официального сайта")
        return value

    @classmethod
    def _products(cls, pages: list[ParsedPage]) -> list[dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for page in pages:
            for node in cls._json_nodes(page.json_ld):
                types = node.get("@type", [])
                types = [types] if isinstance(types, str) else types
                if "Product" not in types or not node.get("name"):
                    continue
                offers = node.get("offers") if isinstance(node.get("offers"), dict) else {}
                name = str(node["name"]).strip()
                found[name.casefold()] = {
                    "name": name,
                    "category": str(node.get("category") or "").strip(),
                    "description": str(node.get("description") or "").strip()[:500],
                    "price": offers.get("price") or node.get("price"),
                    "currency": offers.get("priceCurrency") or node.get("priceCurrency"),
                    "url": str(node.get("url") or page.url),
                    "evidence_url": page.url,
                }
            if any(hint in page.url.casefold() for hint in cls.PRODUCT_HINTS):
                for heading in page.headings[:3]:
                    if 2 <= len(heading.split()) <= 12:
                        found.setdefault(
                            heading.casefold(),
                            {
                                "name": heading,
                                "category": "",
                                "description": page.description[:500],
                                "price": None,
                                "currency": None,
                                "url": page.url,
                                "evidence_url": page.url,
                            },
                        )
        return list(found.values())

    @staticmethod
    def _json_nodes(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for value in values:
            graph = value.get("@graph")
            nodes.extend(item for item in graph if isinstance(item, dict)) if isinstance(
                graph, list
            ) else nodes.append(value)
        return nodes

    @staticmethod
    def _categories(pages: list[ParsedPage], products: list[dict[str, Any]]) -> list[str]:
        values = {str(item["category"]).strip() for item in products if item.get("category")}
        for page in pages:
            for heading in page.headings:
                lowered = heading.casefold()
                if any(
                    token in lowered
                    for token in ("сывор", "крем", "serum", "cream", "маск", "cleanser", "уход")
                ):
                    values.add(heading)
        return sorted(values, key=str.casefold)

    @staticmethod
    def _attributes(pages: list[ParsedPage], products: list[dict[str, Any]]) -> list[str]:
        text = " ".join(
            [item.get("description", "") for item in products]
            + [page.description for page in pages]
        ).casefold()
        vocabulary = {
            "увлажняющий": ("увлажняющ",),
            "омолаживающий": ("омолаживающ",),
            "чувствительная кожа": ("чувствительн",),
            "проблемная кожа": ("проблемн",),
            "гиалуроновая кислота": ("гиалуронов",),
            "витамин c": ("витамин c",),
            "ниацинамид": ("ниацинамид",),
            "retinol": ("retinol",),
            "hydrating": ("hydrating",),
            "sensitive skin": ("sensitive skin",),
            "anti-aging": ("anti-aging",),
            "acne": ("acne",),
            "barrier": ("barrier",),
        }
        return [
            canonical
            for canonical, forms in vocabulary.items()
            if any(form in text for form in forms)
        ]
