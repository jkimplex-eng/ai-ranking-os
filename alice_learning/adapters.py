from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from alice_learning.ports import AliceEvidenceRecord
from organization_workspace.models import Organization, OrganizationProject
from publication_learning.repository import PublicationLearningRepository
from research.models import Research, ResearchTask, Response, ResponseProcessingStatus
from research.scoring import response_recommends_target
from yandex_intelligence.models import YandexIntelligenceSnapshot


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").casefold().removeprefix("www.")


class ResearchAliceEvidenceSource:
    """Framework adapter. Domain learning code consumes only AliceEvidenceRecord values."""

    FEATURE_VERSION = "1.0"

    def __init__(self, db: Session) -> None:
        self.db = db

    def records(self, organization_id: int, research_id: int) -> list[AliceEvidenceRecord]:
        research = self.db.scalar(
            select(Research)
            .options(
                selectinload(Research.tasks)
                .selectinload(ResearchTask.responses)
                .selectinload(Response.extracted_citations),
                selectinload(Research.tasks)
                .selectinload(ResearchTask.responses)
                .selectinload(Response.extracted_recommendations),
            )
            .where(Research.id == research_id)
        )
        if research is None:
            raise LookupError(f"Research {research_id} not found")
        declared_org = research.metadata_payload.get("organization_id")
        if declared_org is not None and int(declared_org) != organization_id:
            raise PermissionError("Исследование принадлежит другой организации")

        metadata = research.metadata_payload or {}
        brand = str(
            metadata.get("brand") or metadata.get("target_entity") or research.title
        ).strip()
        profile = (
            metadata.get("brand_profile") if isinstance(metadata.get("brand_profile"), dict) else {}
        )
        category = str(
            metadata.get("research_profile")
            or (profile.get("categories") or ["UNIVERSAL"])[0]
            or "UNIVERSAL"
        ).upper()
        language = self._first(metadata, "languages", "language", "ru").lower()
        region = self._first(metadata, "regions", "region", "RU").upper()
        website = str(metadata.get("website_url") or profile.get("website_url") or "")
        brand_domain = _domain(website)
        query_facts, webmaster = self._yandex_facts(organization_id)

        records: list[AliceEvidenceRecord] = []
        for task in research.tasks:
            if (task.provider or "").casefold() not in {"yandex", "yandexgpt"}:
                continue
            fact = query_facts.get(_normalize(task.query), {})
            for response in task.responses:
                if response.processing_status != ResponseProcessingStatus.PROCESSED:
                    continue
                citations = response.extracted_citations or []
                urls = [item.url for item in citations if item.url]
                if not urls:
                    urls = [
                        str(value.get("url", ""))
                        for value in response.normalized_response.get("citations", [])
                        if isinstance(value, dict) and value.get("url")
                    ]
                domains = list(dict.fromkeys(_domain(url) for url in urls if _domain(url)))
                independent = [value for value in domains if value != brand_domain]
                features, evidence = self._features(
                    fact=fact,
                    webmaster=webmaster,
                    profile=profile,
                    independent_source_count=len(independent),
                )
                rank = min(
                    (
                        item.rank
                        for item in response.extracted_recommendations
                        if brand.casefold() in item.content.casefold()
                    ),
                    default=None,
                )
                records.append(
                    AliceEvidenceRecord(
                        research_id=research.id,
                        response_id=response.id,
                        brand=brand,
                        query=task.query,
                        category=category,
                        language=language,
                        region=region,
                        provider=response.provider,
                        model=response.model,
                        mentioned=brand.casefold() in response.content.casefold(),
                        recommended=response_recommends_target(response, brand.casefold()),
                        cited=bool(domains),
                        recommendation_rank=rank,
                        source_domains=domains,
                        features=features,
                        feature_evidence=evidence,
                        evidence_status=(
                            "MEASURED"
                            if sum(item["status"] == "MEASURED" for item in evidence.values()) >= 5
                            else "PARTIAL"
                        ),
                        observed_at=response.finished_at,
                    )
                )
        return records

    def _yandex_facts(self, organization_id: int) -> tuple[dict[str, dict], dict]:
        snapshot = self.db.scalar(
            select(YandexIntelligenceSnapshot)
            .where(YandexIntelligenceSnapshot.organization_id == organization_id)
            .order_by(
                YandexIntelligenceSnapshot.created_at.desc(),
                YandexIntelligenceSnapshot.id.desc(),
            )
        )
        if snapshot is None:
            return {}, {}
        facts = {
            _normalize(str(item.get("query", ""))): item
            for item in snapshot.query_map
            if item.get("query")
        }
        return facts, snapshot.webmaster_evidence or {}

    @staticmethod
    def _features(
        *, fact: dict, webmaster: dict, profile: dict, independent_source_count: int
    ) -> tuple[dict[str, float], dict]:
        position = fact.get("position")
        search_visibility = (
            max(0.0, min(1.0, 1 - (float(position) - 1) / 99)) if position is not None else 0.5
        )
        products = profile.get("products") if isinstance(profile.get("products"), list) else []
        attributes = (
            profile.get("attributes") if isinstance(profile.get("attributes"), list) else []
        )
        completeness_parts = (
            bool(str(profile.get("description", "")).strip()),
            bool(products),
            bool(attributes),
        )
        content_completeness = sum(completeness_parts) / len(completeness_parts)
        evidence_urls = (
            profile.get("evidence_urls") if isinstance(profile.get("evidence_urls"), list) else []
        )
        expertise = min(1.0, len(evidence_urls) / 3) if evidence_urls else 0.5
        availability_values = [
            bool(item.get("price")) and bool(item.get("url"))
            for item in products
            if isinstance(item, dict)
        ]
        availability = (
            sum(availability_values) / len(availability_values) if availability_values else 0.5
        )
        problems = webmaster.get("diagnostics", {}).get("problems", {})
        present = sum(
            isinstance(value, dict) and value.get("state") == "PRESENT"
            for value in problems.values()
        )
        technical = max(0.0, 1 - present / 5) if problems else 0.5
        features = {
            "search_visibility": round(search_visibility, 6),
            "landing_page_match": 1.0 if fact.get("url") else 0.0,
            "independent_source_support": round(min(1.0, independent_source_count / 5), 6),
            "content_completeness": round(content_completeness, 6),
            "expertise_evidence": round(expertise, 6),
            "freshness": 0.5,
            "availability_clarity": round(availability, 6),
            "technical_health": round(technical, 6),
        }
        evidence = {
            "search_visibility": {
                "status": "MEASURED" if position is not None else "NOT_MEASURED",
                "source": "Yandex Webmaster",
                "value": position,
            },
            "landing_page_match": {
                "status": "MEASURED" if fact else "NOT_MEASURED",
                "source": "Yandex Webmaster",
                "value": fact.get("url"),
            },
            "independent_source_support": {
                "status": "MEASURED",
                "source": "Сохранённый ответ",
                "value": independent_source_count,
            },
            "content_completeness": {
                "status": "MEASURED" if profile else "NOT_MEASURED",
                "source": "Профиль бренда",
                "value": sum(completeness_parts),
            },
            "expertise_evidence": {
                "status": "MEASURED" if evidence_urls else "NOT_MEASURED",
                "source": "Профиль бренда",
                "value": len(evidence_urls),
            },
            "freshness": {
                "status": "NOT_MEASURED",
                "source": None,
                "value": None,
            },
            "availability_clarity": {
                "status": "MEASURED" if availability_values else "NOT_MEASURED",
                "source": "Карточки продуктов",
                "value": len(availability_values),
            },
            "technical_health": {
                "status": "MEASURED" if problems else "NOT_MEASURED",
                "source": "Yandex Webmaster",
                "value": present if problems else None,
            },
        }
        return features, evidence

    @staticmethod
    def _first(metadata: dict, plural: str, singular: str, default: str) -> str:
        value = metadata.get(plural, metadata.get(singular, default))
        return str(value[0] if isinstance(value, list) and value else value or default)


class PublicationInfluenceSource:
    """Public-shaped adapter over the existing publication learning repository."""

    def __init__(self, db: Session) -> None:
        self.repository = PublicationLearningRepository(db)

    def factors(self, *, category: str, language: str, region: str) -> list[dict]:
        result = []
        for item in self.repository.estimates(
            {"metric": "recommendation_score", "language": language, "region": region}
        ):
            if item.provider.casefold() not in {"all", "yandex", "yandexgpt"}:
                continue
            if category != "UNIVERSAL" and item.category not in {category, "UNIVERSAL"}:
                continue
            result.append(
                {
                    "resource_domain": item.resource_domain,
                    "expected_delta": item.expected_delta,
                    "confidence_min": item.confidence_min,
                    "confidence_max": item.confidence_max,
                    "confidence_score": item.confidence_score,
                    "sample_size": item.sample_size,
                    "evidence_level": item.evidence_level,
                    "controlled_experiments": item.controlled_experiments,
                    "algorithm_version": item.algorithm_version,
                }
            )
        return result


class ResearchOrganizationSource:
    """Resolve tenant ownership at the adapter boundary for background ingestion."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def organization_id(self, research_id: int) -> int | None:
        research = self.db.get(Research, research_id)
        if research is None:
            return None
        declared = (research.metadata_payload or {}).get("organization_id")
        if declared is not None:
            return int(declared)
        if research.project_id is not None:
            value = self.db.scalar(
                select(OrganizationProject.organization_id).where(
                    OrganizationProject.project_id == research.project_id
                )
            )
            if value is not None:
                return int(value)
        if self.db.scalar(select(func.count()).select_from(Organization)) == 1:
            return self.db.scalar(select(Organization.id))
        return None

    def research_ids(self, organization_id: int) -> list[int]:
        project_ids = set(
            self.db.scalars(
                select(OrganizationProject.project_id).where(
                    OrganizationProject.organization_id == organization_id
                )
            )
        )
        result = []
        for research in self.db.scalars(select(Research).order_by(Research.created_at)):
            declared = (research.metadata_payload or {}).get("organization_id")
            belongs = declared is not None and int(declared) == organization_id
            belongs = belongs or (
                research.project_id is not None and research.project_id in project_ids
            )
            if declared is None and research.project_id is None:
                belongs = self.organization_id(research.id) == organization_id
            if belongs and any(
                (task.provider or "").casefold() in {"yandex", "yandexgpt"}
                for task in research.tasks
            ):
                result.append(research.id)
        return result
