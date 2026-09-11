# Research Laboratory

Read-only composition layer for reproducible research provenance. It combines persisted Research,
Response, extraction, scoring and linked graph artifacts without calling an LLM or changing their
contracts.

## Public API

- `GET /research/{id}/laboratory` — model evidence, sources, entities, graph and timeline.
- `GET /research/diff?left={id}&right={id}` — deterministic comparison of two persisted runs.
- `POST /research-publications` — record a publication intervention.
- `POST /research-publications/{id}/observations` — record provider/model first observation.
- `GET /research-publications?entity_id={uuid}` — publication and observation history.

The laboratory deliberately returns `NOT_CALCULATED`/`NOT_RECORDED` states instead of inventing
per-model Visibility, domain authority, graph evidence, indexing speed, or causal impact.
