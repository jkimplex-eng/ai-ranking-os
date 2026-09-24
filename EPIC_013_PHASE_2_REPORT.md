# EPIC-013 Phase 2 — Research Core Completion

## Outcome

AI Ranking OS now exposes a research laboratory over persisted evidence. A user can trace aggregate
scores to model responses, prompts, extracted entities, citations, graph evidence and timestamps.
The implementation does not perform provider calls on reads and does not invent unsupported values.

## Implemented

- Research provenance and per-response numerator contributions.
- Model Explorer with prompt, response, extraction, region/language, latency, tokens, cost and time.
- Source Intelligence with URL/domain grouping, provider/model usage and exact Citation v1 points.
- Citation zero-state through the existing report methodology and response evidence.
- Entity Explorer with aliases, occurrences, source IDs and knowledge graph IDs.
- Graph provenance contract with directed edges and explicit `NOT_RECORDED` evidence state.
- Publication interventions and earliest provider/model observations.
- Chronological research timeline based exclusively on persisted timestamps.
- Deterministic arbitrary-research Diff API for metrics, responses, entities, sources and signals.
- Recommendation evidence enrichment with affected models and missing-source state.
- Research-oriented report UI with honest empty states and causal-disclaimer labels.

## Data and migration

- Alembic revision: `0072` (down revision `0071`).
- Tables: `research_publications`, `publication_observations`.
- A unique publication/provider/model observation retains the earliest submitted timestamp.

## New API

- `GET /research/{research_id}/laboratory`
- `GET /research/diff?left=&right=`
- `POST /research-publications`
- `GET /research-publications?entity_id=`
- `POST /research-publications/{publication_id}/observations`

## Validation

- Ruff: PASS.
- Pytest: PASS, 291 tests total (287 existing + 4 new).
- Compileall: PASS.
- OpenAPI: PASS, 232 paths.
- TypeScript: PASS.
- ESLint: PASS.
- Frontend build: PASS.
- Playwright: PASS, 4 active tests; 2 production-only tests skipped by their environment guard.
- Phase 2 specification validation: PASS, 100/100 strict score.

## Honest limitations

- Scoring v1.0 has no per-model Visibility contract. The UI therefore shows observed signals and
  numerator contributions, never fabricated model scores or model weights.
- Domain Authority and provider indexing characteristics are not measured and remain explicitly
  unavailable. The AI Index Observatory must be populated from measured observations, not a static
  marketing matrix.
- Publication before/after changes are correlation. Causality is not claimed without a controlled
  experiment.
- Historical graph snapshots are displayed only when a research stores a snapshot link. Unlinked
  research shows a precise reason rather than the latest unrelated graph.
- Local Docker/PostgreSQL tooling was unavailable. The project migration chain cannot be validated on
  SQLite because historical revision `0012` uses PostgreSQL constraint alteration; PostgreSQL
  upgrade/downgrade remains a CI/deployment gate.
