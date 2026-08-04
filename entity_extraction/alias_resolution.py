from entity_extraction.deduplication import normalize_name
from entity_extraction.schemas import ExtractedEntity, ResolutionLog

KNOWN_ALIASES = {
    "openai": "OpenAI",
    "openaiinc": "OpenAI",
    "msft": "Microsoft",
    "microsoftcorp": "Microsoft",
    "ibm": "International Business Machines",
    "alphabet": "Google",
    "googlellc": "Google",
}


def _acronym(name: str) -> str:
    words = [word for word in name.replace("-", " ").split() if word]
    return "".join(word[0] for word in words).casefold() if len(words) > 1 else ""


def resolve_aliases(
    entities: list[ExtractedEntity],
) -> tuple[list[ExtractedEntity], dict[str, str], list[ResolutionLog]]:
    canonical_by_key: dict[tuple[str, str], ExtractedEntity] = {}
    id_map: dict[str, str] = {entity.temp_id: entity.temp_id for entity in entities}
    logs: list[ResolutionLog] = []

    for entity in entities:
        normalized = normalize_name(entity.name)
        canonical_name = KNOWN_ALIASES.get(normalized, entity.name)
        if len(entity.name) <= 8:
            for candidate in entities:
                if candidate.temp_id != entity.temp_id and _acronym(candidate.name) == normalized:
                    canonical_name = candidate.name
                    break
        key = (normalize_name(canonical_name), entity.entity_type)
        existing = canonical_by_key.get(key)
        if existing is None:
            if canonical_name != entity.name:
                entity.aliases = sorted(set(entity.aliases + [entity.name]))
                entity.name = canonical_name
            canonical_by_key[key] = entity
            continue
        id_map[entity.temp_id] = existing.temp_id
        existing.aliases = sorted(set(existing.aliases + entity.aliases + [entity.name]))
        existing.confidence = max(existing.confidence, entity.confidence)
        logs.append(
            ResolutionLog(
                stage="alias_resolution",
                action="resolve",
                details={
                    "alias_id": entity.temp_id,
                    "canonical_id": existing.temp_id,
                    "canonical_name": existing.name,
                },
            )
        )
    return list(canonical_by_key.values()), id_map, logs

