from __future__ import annotations

import html
import ipaddress
import re
import socket
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from competitor_intelligence.models import CompetitorSocialPost, CompetitorSocialSource
from competitor_intelligence.repository import CompetitorIntelligenceRepository
from competitor_intelligence.schemas import (
    SocialDashboardRead,
    SocialPlatform,
    SocialPostRead,
    SocialSourceCreate,
    SocialSourceRead,
)
from provider_connections.crypto import SecretCipher
from workspace.repository import CompetitorRepository, ProjectRepository, WorkspaceRepository


class SocialMonitorError(ValueError):
    pass


@dataclass
class CollectedPost:
    external_id: str
    url: str
    title: str | None
    content: str
    published_at: datetime
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None


@dataclass(frozen=True)
class DiscoveredSource:
    platform: SocialPlatform
    profile_url: str
    external_id: str


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


class SocialCollectorPort(Protocol):
    def collect(self, source: CompetitorSocialSource, token: str | None) -> list[CollectedPost]: ...


class SocialDiscoveryPort(Protocol):
    def discover(self, domains: list[str]) -> list[DiscoveredSource]: ...


class WebsiteSocialDiscovery:
    """Discover only social profiles explicitly linked by the competitor's own website."""

    _hosts = {
        "t.me": SocialPlatform.TELEGRAM,
        "telegram.me": SocialPlatform.TELEGRAM,
        "youtube.com": SocialPlatform.YOUTUBE,
        "www.youtube.com": SocialPlatform.YOUTUBE,
        "youtu.be": SocialPlatform.YOUTUBE,
        "vk.com": SocialPlatform.VK,
        "www.vk.com": SocialPlatform.VK,
        "instagram.com": SocialPlatform.INSTAGRAM,
        "www.instagram.com": SocialPlatform.INSTAGRAM,
    }

    def discover(self, domains: list[str]) -> list[DiscoveredSource]:
        found: dict[tuple[SocialPlatform, str], DiscoveredSource] = {}
        for raw_domain in domains[:5]:
            try:
                page_url = self._website_url(raw_domain)
                response = HttpSocialCollector._get(page_url)
            except (SocialMonitorError, httpx.HTTPError):
                continue
            parser = _LinkParser()
            parser.feed(response.text)
            for href in parser.links:
                candidate = self._source(urljoin(str(response.url), href))
                if candidate:
                    found[(candidate.platform, candidate.external_id.casefold())] = candidate
        return list(found.values())

    @staticmethod
    def _website_url(raw_domain: str) -> str:
        value = raw_domain.strip()
        url = value if value.startswith(("http://", "https://")) else f"https://{value}"
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or not host:
            raise SocialMonitorError("Некорректный домен конкурента")
        try:
            addresses = {
                item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            }
        except socket.gaierror as error:
            raise SocialMonitorError("Домен конкурента не разрешается") from error
        if any(
            ipaddress.ip_address(address).is_private
            or ipaddress.ip_address(address).is_loopback
            or ipaddress.ip_address(address).is_link_local
            for address in addresses
        ):
            raise SocialMonitorError("Локальные адреса нельзя использовать для автообнаружения")
        return url

    @classmethod
    def _source(cls, url: str) -> DiscoveredSource | None:
        parsed = urlparse(url)
        platform = cls._hosts.get((parsed.hostname or "").casefold())
        parts = [part for part in parsed.path.split("/") if part]
        if platform is None or not parts:
            return None
        if (parsed.hostname or "").casefold() == "youtu.be":
            return None
        ignored = {"share", "intent", "watch", "results", "reel", "reels", "stories", "p"}
        if parts[0].casefold() in ignored:
            return None
        is_youtube_path = (
            platform == SocialPlatform.YOUTUBE
            and parts[0] in {"channel", "c", "user"}
            and len(parts) > 1
        )
        external_id = parts[1] if is_youtube_path else parts[0]
        external_id = external_id.lstrip("@").strip()
        if not external_id:
            return None
        profile_url = f"{parsed.scheme}://{parsed.netloc}/{'/'.join(parts[:2])}"
        return DiscoveredSource(platform, profile_url, external_id)


class HttpSocialCollector:
    def collect(self, source: CompetitorSocialSource, token: str | None) -> list[CollectedPost]:
        platform = SocialPlatform(source.platform)
        if platform == SocialPlatform.YOUTUBE:
            return self._youtube(source.external_id)
        if platform == SocialPlatform.TELEGRAM:
            return self._telegram(source.external_id)
        if not token:
            raise SocialMonitorError(f"Для {platform.value} нужен официальный API-токен")
        if platform == SocialPlatform.VK:
            return self._vk(source.external_id, token)
        return self._instagram(source.external_id, token)

    @staticmethod
    def _get(url: str, params: dict | None = None) -> httpx.Response:
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "AI-Ranking-OS-Social-Monitor/1.0"},
        ) as client:
            response = client.get(url, params=params)
        response.raise_for_status()
        return response

    def _youtube(self, channel_id: str) -> list[CollectedPost]:
        if not channel_id.startswith("UC"):
            profile = self._get(f"https://www.youtube.com/@{channel_id.lstrip('@')}").text
            match = re.search(r'"channelId":"(UC[\w-]+)"', profile)
            if not match:
                raise SocialMonitorError("YouTube Channel ID не найден")
            channel_id = match.group(1)
        response = self._get("https://www.youtube.com/feeds/videos.xml", {"channel_id": channel_id})
        root = ET.fromstring(response.text)
        ns = {
            "a": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "m": "http://search.yahoo.com/mrss/",
        }
        posts = []
        for entry in root.findall("a:entry", ns):
            video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
            published = entry.findtext("a:published", default="", namespaces=ns)
            community = entry.find("m:group/m:community", ns)
            views = None
            if community is not None:
                stats = community.find("m:statistics", ns)
                views = int(stats.attrib.get("views", "0")) if stats is not None else None
            if video_id and published:
                posts.append(
                    CollectedPost(
                        video_id,
                        f"https://www.youtube.com/watch?v={video_id}",
                        entry.findtext("a:title", default="", namespaces=ns),
                        entry.findtext("a:title", default="", namespaces=ns),
                        datetime.fromisoformat(published.replace("Z", "+00:00")),
                        views=views,
                    )
                )
        return posts

    def _telegram(self, handle: str) -> list[CollectedPost]:
        handle = handle.strip().lstrip("@").split("/")[-1]
        text = self._get(f"https://t.me/s/{handle}").text
        posts = []
        pattern = re.compile(
            r'data-post="([^"]+)"[\s\S]*?class="tgme_widget_message_text[^>]*>'
            r'([\s\S]*?)</div>[\s\S]*?<time datetime="([^"]+)"',
            re.I,
        )
        for post_id, content, published in pattern.findall(text):
            clean = html.unescape(re.sub(r"<[^>]+>", " ", content))
            clean = " ".join(clean.split())
            posts.append(
                CollectedPost(
                    post_id,
                    f"https://t.me/{post_id}",
                    clean[:120] or None,
                    clean,
                    datetime.fromisoformat(published.replace("Z", "+00:00")),
                )
            )
        return posts

    def _vk(self, domain: str, token: str) -> list[CollectedPost]:
        data = self._get(
            "https://api.vk.com/method/wall.get",
            {"domain": domain.lstrip("@"), "count": 50, "access_token": token, "v": "5.199"},
        ).json()
        if data.get("error"):
            raise SocialMonitorError(data["error"].get("error_msg", "VK API error"))
        posts = []
        for item in data.get("response", {}).get("items", []):
            owner = item.get("owner_id")
            post_id = item.get("id")
            posts.append(
                CollectedPost(
                    str(post_id),
                    f"https://vk.com/wall{owner}_{post_id}",
                    None,
                    item.get("text", ""),
                    datetime.fromtimestamp(item["date"], UTC),
                    views=(item.get("views") or {}).get("count"),
                    likes=(item.get("likes") or {}).get("count"),
                    comments=(item.get("comments") or {}).get("count"),
                    shares=(item.get("reposts") or {}).get("count"),
                )
            )
        return posts

    def _instagram(self, profile_id: str, token: str) -> list[CollectedPost]:
        data = self._get(
            f"https://graph.facebook.com/v22.0/{profile_id}/media",
            {
                "fields": "id,caption,permalink,timestamp,like_count,comments_count",
                "limit": 50,
                "access_token": token,
            },
        ).json()
        if data.get("error"):
            raise SocialMonitorError(data["error"].get("message", "Instagram Graph API error"))
        return [
            CollectedPost(
                item["id"],
                item.get("permalink", ""),
                None,
                item.get("caption", ""),
                datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                likes=item.get("like_count"),
                comments=item.get("comments_count"),
            )
            for item in data.get("data", [])
        ]


class CompetitorSocialMonitorService:
    def __init__(
        self,
        db: Session,
        collector: SocialCollectorPort | None = None,
        discovery: SocialDiscoveryPort | None = None,
    ) -> None:
        self.db = db
        self.repository = CompetitorIntelligenceRepository(db)
        self.collector = collector or HttpSocialCollector()
        self.discovery = discovery or WebsiteSocialDiscovery()
        settings = get_settings()
        secret = settings.provider_secret_key or settings.auth_jwt_secret
        self.cipher = SecretCipher(secret) if len(secret) >= 32 else None

    def create(
        self, user_id: int, project_id: int, competitor_id: int, payload: SocialSourceCreate
    ) -> SocialSourceRead:
        self._authorize(user_id, project_id, competitor_id)
        self._validate_host(payload.platform, str(payload.profile_url))
        encrypted = None
        if payload.access_token:
            if self.cipher is None:
                raise SocialMonitorError("На сервере не настроено шифрование секретов")
            encrypted = self.cipher.encrypt(payload.access_token)
        source = self.repository.add_social_source(
            CompetitorSocialSource(
                competitor_id=competitor_id,
                platform=payload.platform.value,
                profile_url=str(payload.profile_url),
                external_id=payload.external_id.strip(),
                encrypted_token=encrypted,
                status="PENDING",
                next_scan_at=datetime.now(UTC),
            )
        )
        self.refresh_source(source)
        return self._source_read(source)

    def dashboard(self, user_id: int, project_id: int, competitor_id: int) -> SocialDashboardRead:
        self._authorize(user_id, project_id, competitor_id)
        sources = [
            self._source_read(source) for source in self.repository.social_sources(competitor_id)
        ]
        return SocialDashboardRead(
            competitor_id=competitor_id,
            sources=sources,
            total_posts=sum(len(source.posts) for source in sources),
        )

    def refresh(self, user_id: int, project_id: int, competitor_id: int) -> SocialDashboardRead:
        self._authorize(user_id, project_id, competitor_id)
        for source in self.repository.social_sources(competitor_id):
            if source.active:
                self.refresh_source(source)
        return self.dashboard(user_id, project_id, competitor_id)

    def discover(self, user_id: int, project_id: int, competitor_id: int) -> SocialDashboardRead:
        competitor = self._authorize(user_id, project_id, competitor_id)
        existing = {
            (item.platform, item.external_id.casefold())
            for item in self.repository.social_sources(competitor_id)
        }
        for candidate in self.discovery.discover(competitor.domains):
            key = (candidate.platform.value, candidate.external_id.casefold())
            if key in existing:
                continue
            source = self.repository.add_social_source(
                CompetitorSocialSource(
                    competitor_id=competitor_id,
                    platform=candidate.platform.value,
                    profile_url=candidate.profile_url,
                    external_id=candidate.external_id,
                    status="DISCOVERED",
                    next_scan_at=datetime.now(UTC),
                )
            )
            self.refresh_source(source)
            existing.add(key)
        return self.dashboard(user_id, project_id, competitor_id)

    def delete(self, user_id: int, project_id: int, competitor_id: int, source_id: int) -> None:
        self._authorize(user_id, project_id, competitor_id)
        source = self.repository.social_source(source_id)
        if source is None or source.competitor_id != competitor_id:
            raise SocialMonitorError("Источник соцсети не найден")
        self.repository.delete_social_source(source)

    def run_due(self) -> int:
        count = 0
        for source in self.repository.due_social_sources(datetime.now(UTC)):
            self.refresh_source(source)
            count += 1
        return count

    def refresh_source(self, source: CompetitorSocialSource) -> None:
        now = datetime.now(UTC)
        try:
            token = (
                self.cipher.decrypt(source.encrypted_token)
                if source.encrypted_token and self.cipher
                else None
            )
            for collected in self.collector.collect(source, token):
                item = self.repository.social_post(source.id, collected.external_id)
                if item is None:
                    item = CompetitorSocialPost(
                        source_id=source.id,
                        external_post_id=collected.external_id,
                        url=collected.url,
                        published_at=collected.published_at,
                    )
                    self.db.add(item)
                item.title = collected.title
                item.content = collected.content
                item.views = collected.views
                item.likes = collected.likes
                item.comments = collected.comments
                item.shares = collected.shares
                interactions = sum(
                    value or 0 for value in (collected.likes, collected.comments, collected.shares)
                )
                item.engagement_rate = (
                    round(interactions / collected.views * 100, 3) if collected.views else None
                )
                item.significance_score = self._significance(collected, interactions)
                item.raw_metrics = {
                    "views": collected.views,
                    "likes": collected.likes,
                    "comments": collected.comments,
                    "shares": collected.shares,
                }
                item.last_seen_at = now
            source.status = "CONNECTED"
            source.last_error = None
        except (SocialMonitorError, httpx.HTTPError, ET.ParseError, ValueError) as error:
            source.status = "NOT_CONFIGURED" if "токен" in str(error).casefold() else "ERROR"
            source.last_error = str(error)[:1000]
        source.last_scanned_at = now
        source.next_scan_at = now + timedelta(days=1)
        self.repository.commit()

    @staticmethod
    def _significance(post: CollectedPost, interactions: int) -> float:
        reach = min((post.views or 0) / 100_000, 1.0)
        engagement = min(interactions / max(post.views or 1, 1) / 0.10, 1.0)
        completeness = (
            sum(value is not None for value in (post.views, post.likes, post.comments, post.shares))
            / 4
        )
        return round((reach * 0.45 + engagement * 0.40 + completeness * 0.15) * 100, 1)

    def _source_read(self, source: CompetitorSocialSource) -> SocialSourceRead:
        return SocialSourceRead(
            id=source.id,
            competitor_id=source.competitor_id,
            platform=source.platform,
            profile_url=source.profile_url,
            external_id=source.external_id,
            configured=source.platform
            in {SocialPlatform.TELEGRAM.value, SocialPlatform.YOUTUBE.value}
            or bool(source.encrypted_token),
            active=source.active,
            status=source.status,
            last_scanned_at=source.last_scanned_at,
            next_scan_at=source.next_scan_at,
            last_error=source.last_error,
            posts=[
                SocialPostRead.model_validate(item, from_attributes=True)
                for item in self.repository.social_posts(source.id)
            ],
        )

    def _authorize(self, user_id: int, project_id: int, competitor_id: int):
        workspace = WorkspaceRepository(self.db).get_or_create(user_id)
        ProjectRepository(self.db).get(workspace.id, project_id)
        return CompetitorRepository(self.db).get(project_id, competitor_id)

    @staticmethod
    def _validate_host(platform: SocialPlatform, url: str) -> None:
        host = (urlparse(url).hostname or "").casefold()
        allowed = {
            SocialPlatform.TELEGRAM: {"t.me", "telegram.me"},
            SocialPlatform.YOUTUBE: {"youtube.com", "www.youtube.com", "youtu.be"},
            SocialPlatform.VK: {"vk.com", "www.vk.com"},
            SocialPlatform.INSTAGRAM: {"instagram.com", "www.instagram.com"},
        }
        if host not in allowed[platform]:
            raise SocialMonitorError(f"URL не принадлежит платформе {platform.value}")
