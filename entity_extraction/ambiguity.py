from collections import defaultdict

from entity_extraction.deduplication import normalize_name
from entity_extraction.schemas import ExtractedEntity, ResolutionLog


def resolve_ambiguity(
    entities: list[ExtractedEntity],
) -> tuple[list[ExtractedEntity], list[ResolutionLog]]:
    by_surface: dict[str, list[ExtractedEntity]] = defaultdict(list)
    for entity in entities:
        by_surface[normalize_name(entity.name)].append(entity)

    logs = []
    for name, candidates in by_surface.items():
        if len({candidate.entity_type for candidate in candidates}) <= 1:
            continue
        for candidate in candidates:
            candidate.confidence = round(candidate.confidence * 0.85, 4)
        logs.append(
            ResolutionLog(
                stage="ambiguity_resolution",
                action="retain_candidates",
                details={
                    "surface": name,
                    "candidate_types": sorted(
                        {candidate.entity_type for candidate in candidates}
                    ),
                },
            )
        )
    return entities, logs

