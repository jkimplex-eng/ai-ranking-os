from typing import Any

from entity_extraction.schemas import ExtractionResult


def build_graph(
    extraction: ExtractionResult,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    return {
        "correlation_id": correlation_id,
        "nodes": [
            {
                "id": entity.knowledge_graph_id,
                "label": entity.canonical_name,
                "type": entity.entity_type,
                "confidence": entity.confidence,
            }
            for entity in extraction.entities
        ],
        "edges": [relation.model_dump(mode="json") for relation in extraction.relations],
        "version": "1.0",
    }

