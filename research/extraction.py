import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from entity_extraction.entity_types import EntityType
from entity_extraction.pipeline import run_pipeline
from entity_extraction.schemas import ExtractionInput
from research.models import (
    ExtractedCitation,
    ExtractedEntity,
    ExtractedRecommendation,
    Response,
    ResponseProcessingStatus,
)
from research.normalizer import NormalizedResponse
from research.repositories import EntityNotFoundError
from research.schemas import ExtractionResultRead
from research.scoring import ScoringService

RECOMMENDATION_PATTERN = re.compile(
    r"(?im)^(?:[-*]\s*|\d+[.)]\s*)?"
    r"(?P<content>.*(?:recommend|suggest|совету|рекоменду)[^\n.!?]*(?:[.!?]|$))"
)


class ExtractionProcessingError(RuntimeError):
    """Normalized response could not be processed."""


class ExtractionService:
    """Provider-independent extraction from the unified response contract."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def extract(self, response_id: int) -> ExtractionResultRead:
        response = self.db.get(Response, response_id)
        if response is None:
            raise EntityNotFoundError(f"Response {response_id} not found")
        research_id = response.research_task.research_id
        try:
            normalized = NormalizedResponse.model_validate(
                response.normalized_response
            )
            self._replace_results(response, normalized)
            response.processing_status = ResponseProcessingStatus.PROCESSED
            response.processing_error = None
            self.db.commit()
        except Exception as error:
            self.db.rollback()
            failed_response = self.db.get(Response, response_id)
            if failed_response is not None:
                failed_response.processing_status = ResponseProcessingStatus.FAILED
                failed_response.processing_error = str(error)
                self.db.commit()
            raise ExtractionProcessingError(
                f"Response {response_id} extraction failed: {error}"
            ) from error
        ScoringService(self.db).calculate_if_ready(research_id)
        return self.get(response_id)

    def get(self, response_id: int) -> ExtractionResultRead:
        response = self.db.get(Response, response_id)
        if response is None:
            raise EntityNotFoundError(f"Response {response_id} not found")
        entities = list(
            self.db.scalars(
                select(ExtractedEntity)
                .where(ExtractedEntity.response_id == response_id)
                .order_by(ExtractedEntity.id)
            )
        )
        citations = list(
            self.db.scalars(
                select(ExtractedCitation)
                .where(ExtractedCitation.response_id == response_id)
                .order_by(ExtractedCitation.position, ExtractedCitation.id)
            )
        )
        recommendations = list(
            self.db.scalars(
                select(ExtractedRecommendation)
                .where(ExtractedRecommendation.response_id == response_id)
                .order_by(ExtractedRecommendation.rank, ExtractedRecommendation.id)
            )
        )

        def by_type(entity_type: EntityType) -> list[ExtractedEntity]:
            return [item for item in entities if item.entity_type == entity_type]

        return ExtractionResultRead(
            response_id=response.id,
            status=response.processing_status,
            entities=entities,
            brands=by_type(EntityType.BRAND),
            products=by_type(EntityType.PRODUCT),
            organizations=by_type(EntityType.ORGANIZATION),
            people=by_type(EntityType.PERSON),
            citations=citations,
            recommendations=recommendations,
        )

    def _replace_results(
        self,
        response: Response,
        normalized: NormalizedResponse,
    ) -> None:
        response.extracted_entities.clear()
        response.extracted_citations.clear()
        response.extracted_recommendations.clear()
        raw_input: dict[str, Any] = {"content": normalized.content}
        structured_entities = _structured_entities(normalized.metadata)
        if structured_entities:
            raw_input["entities"] = structured_entities
        pipeline_result = run_pipeline(
            ExtractionInput(
                response_id=str(response.id),
                raw_response=raw_input,
                model=response.model,
            )
        )
        response.extracted_entities.extend(
            ExtractedEntity(
                name=entity.name,
                canonical_name=entity.canonical_name,
                entity_type=str(entity.entity_type),
                confidence=entity.confidence,
                aliases=entity.aliases,
                knowledge_graph_id=entity.knowledge_graph_id,
                metadata_payload={"entity_id": entity.entity_id},
            )
            for entity in pipeline_result.entities
        )
        response.extracted_citations.extend(
            self._citations(normalized.citations)
        )
        response.extracted_recommendations.extend(
            self._recommendations(normalized)
        )

    @staticmethod
    def _citations(
        citations: list[dict[str, Any]],
    ) -> list[ExtractedCitation]:
        results = []
        for position, citation in enumerate(citations, start=1):
            known = {"url", "title", "source", "excerpt"}
            results.append(
                ExtractedCitation(
                    url=_optional_text(citation.get("url")),
                    title=_optional_text(citation.get("title")),
                    source=_optional_text(citation.get("source")),
                    excerpt=_optional_text(
                        citation.get("excerpt", citation.get("text"))
                    ),
                    position=position,
                    metadata_payload={
                        key: value
                        for key, value in citation.items()
                        if key not in known
                    },
                )
            )
        return results

    @staticmethod
    def _recommendations(
        normalized: NormalizedResponse,
    ) -> list[ExtractedRecommendation]:
        structured = normalized.metadata.get("recommendations", [])
        values: list[tuple[str, float, dict[str, Any]]] = []
        if isinstance(structured, list):
            for item in structured:
                if isinstance(item, str):
                    values.append((item, 0.9, {}))
                elif isinstance(item, dict):
                    content = item.get("content", item.get("text"))
                    if content:
                        values.append(
                            (
                                str(content),
                                float(item.get("confidence", 0.9)),
                                {
                                    key: value
                                    for key, value in item.items()
                                    if key not in {"content", "text", "confidence"}
                                },
                            )
                        )
        if not values:
            values = [
                (match.group("content").strip(), 0.7, {"source": "text"})
                for match in RECOMMENDATION_PATTERN.finditer(normalized.content)
            ]
        return [
            ExtractedRecommendation(
                content=content,
                rank=rank,
                confidence=max(0.0, min(confidence, 1.0)),
                metadata_payload=metadata,
            )
            for rank, (content, confidence, metadata) in enumerate(values, start=1)
        ]


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _structured_entities(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    typed_keys = {
        "brands": EntityType.BRAND,
        "products": EntityType.PRODUCT,
        "organizations": EntityType.ORGANIZATION,
        "people": EntityType.PERSON,
    }
    raw_entities = metadata.get("entities", [])
    if isinstance(raw_entities, list):
        for item in raw_entities:
            if isinstance(item, str):
                results.append({"name": item})
            elif isinstance(item, dict):
                results.append(item)
    for key, entity_type in typed_keys.items():
        items = metadata.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, str):
                results.append({"name": item, "type": entity_type})
            elif isinstance(item, dict):
                results.append({"type": entity_type, **item})
    return results
