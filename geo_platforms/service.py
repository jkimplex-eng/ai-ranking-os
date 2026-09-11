from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

from geo_platforms.models import GeoPlatform, GeoPlatformImport
from geo_platforms.repository import PlatformRepository
from geo_platforms.schemas import DiscoveryRequest, ImportRequest, PlatformCreate, PlatformUpdate


class PlatformNotFoundError(LookupError):
    pass


def normalize_domain(value: str) -> str:
    raw = value.strip().lower()
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    domain = (parsed.hostname or "").strip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or "." not in domain or " " in domain:
        raise ValueError("A valid publication domain is required")
    return domain.encode("idna").decode("ascii")


class PlatformService:
    IMPORT_SOURCES = {"AHREFS", "SEMRUSH", "MANUAL"}

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def create(self, payload: PlatformCreate) -> GeoPlatform:
        if self.repository.by_domain(payload.domain):
            raise ValueError(f"Platform domain {payload.domain} already exists")
        return self.repository.save(GeoPlatform(**payload.model_dump()))

    def update(self, platform_id: UUID, payload: PlatformUpdate) -> GeoPlatform:
        item = self._get(platform_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        item.updated_at = datetime.now(UTC)
        return self.repository.save(item)

    def delete(self, platform_id: UUID) -> None:
        self.repository.delete(self._get(platform_id))

    def import_rows(self, payload: ImportRequest) -> GeoPlatformImport:
        provider = payload.provider.upper()
        if provider not in self.IMPORT_SOURCES:
            raise ValueError("provider must be AHREFS, SEMRUSH, or MANUAL")
        imported = 0
        errors: list[dict] = []
        for index, row in enumerate(payload.rows):
            try:
                normalized = self._normalize_import_row(provider, row)
                domain = normalized["domain"]
                item = self.repository.by_domain(domain)
                if item is None:
                    item = GeoPlatform(name=normalized.pop("name"), domain=domain)
                for key, value in normalized.items():
                    setattr(item, key, value)
                item.source = provider
                item.updated_at = datetime.now(UTC)
                self.repository.save(item)
                imported += 1
            except (TypeError, ValueError) as error:
                errors.append({"row": index, "error": str(error)})
        return self.repository.save_import(
            GeoPlatformImport(
                provider=provider,
                status="COMPLETED" if not errors else "PARTIAL",
                rows_total=len(payload.rows),
                rows_imported=imported,
                rows_failed=len(errors),
                errors=errors,
            )
        )

    def discover(self, payload: DiscoveryRequest) -> tuple[int, int, list[GeoPlatform]]:
        created = 0
        existing = 0
        found: list[GeoPlatform] = []
        seen: set[str] = set()
        for url in payload.urls:
            domain = normalize_domain(url)
            if domain in seen:
                continue
            seen.add(domain)
            item = self.repository.by_domain(domain)
            if item is None:
                item = self.repository.save(
                    GeoPlatform(
                        name=domain,
                        domain=domain,
                        category=payload.category,
                        language=payload.language,
                        source="DISCOVERY",
                        source_reference=url,
                        evidence={"discovered_from": [url]},
                    )
                )
                created += 1
            else:
                existing += 1
            found.append(item)
        return created, existing, found

    def _get(self, platform_id: UUID) -> GeoPlatform:
        item = self.repository.get(platform_id)
        if item is None:
            raise PlatformNotFoundError(f"Platform {platform_id} not found")
        return item

    @staticmethod
    def _normalize_import_row(provider: str, row: dict) -> dict:
        domain = normalize_domain(str(row.get("domain") or row.get("url") or ""))
        aliases = {
            "domain_rating": "domain_trust",
            "authority_score": "domain_trust",
            "topical_authority": "topical_authority_score",
            "brand_mentions": "branded_mentions_90d",
            "search_volume": "branded_search_volume",
        }
        allowed = {
            "domain_trust",
            "topical_authority_score",
            "branded_mentions_90d",
            "branded_search_volume",
            "ai_citation_history",
            "youtube_mentions",
            "branded_anchors",
        }
        result: dict = {
            "domain": domain,
            "name": str(row.get("name") or domain),
            "source_reference": str(row.get("source_reference") or provider),
            "evidence": {"provider": provider, "raw": row},
        }
        for raw_key, value in row.items():
            key = aliases.get(raw_key, raw_key)
            if key in allowed and value not in (None, ""):
                normalized_value = (
                    float(value)
                    if key
                    not in {
                        "branded_mentions_90d",
                        "ai_citation_history",
                        "youtube_mentions",
                        "branded_anchors",
                    }
                    else int(value)
                )
                if normalized_value < 0:
                    raise ValueError(f"{key} must be non-negative")
                if key in {"domain_trust", "topical_authority_score"} and normalized_value > 100:
                    raise ValueError(f"{key} must be between 0 and 100")
                result[key] = normalized_value
        return result
