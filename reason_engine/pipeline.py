from typing import Any

from entity_extraction.schemas import ExtractionResult


def build_reasoning_context(
    extraction: ExtractionResult,
    *,
    correlation_id: str,
    query: str,
) -> dict[str, Any]:
    subject = (
        extraction.entities[0].canonical_name
        if extraction.entities
        else query[:100]
    )
    evidence = [
        {
            "entity": entity.canonical_name,
            "type": entity.entity_type,
            "confidence": entity.confidence,
        }
        for entity in extraction.entities
    ]
    return {
        "correlation_id": correlation_id,
        "subject": subject,
        "entity_count": len(extraction.entities),
        "relation_count": len(extraction.relations),
        "evidence": evidence,
        "conclusion": f"Validated evidence for {subject}",
        "version": "1.0",
    }

