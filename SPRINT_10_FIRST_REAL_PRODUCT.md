# Sprint 10 — First Real Product

## Status

**IMPLEMENTED — ready for Pull Request architecture review.** Sprint 11 was not started.

## Completed tasks

- **TASK-1001:** Research Wizard review/run orchestration for entity, models, languages, regions,
  prompt and research templates.
- **TASK-1002:** versioned Prompt Library with create, update, list/get, clone, activate and
  deprecate operations. Six required categories are seeded.
- **TASK-1003:** six read-only research templates with the complete product pipeline.
- **TASK-1004:** all ten provider families validated. `local` remains the backward-compatible
  Ollama identifier. Retry with exponential backoff was added to the HTTP transport; timeout,
  authentication, streaming, usage, pricing, health and availability contracts are tested.
- **TASK-1005:** automatic Research → Provider → Response → Normalization → Extraction → Graph →
  Scoring → Recommendations → Analytics → Insights → Report pipeline.
- **TASK-1006:** unified report containing executive summary, scores, trend, benchmark, insights,
  recommendations, graph, entities, sources and provider execution statistics.
- **TASK-1007:** API/E2E validation proves every persisted transition without manual calls.
- **TASK-1008:** one-command Skinjestique demo writes a reproducible JSON report.

## First working user scenario

The user submits `POST /research/wizard/review`, confirms the rendered prompt and selected provider
capabilities, then submits `POST /research/wizard/run`. The application creates the Research,
automatically executes all selected models and every downstream engine, and returns a completed
Research plus its report URL. `GET /research/{id}/final-report` returns the same persisted aggregate.

The verified demo used OpenAI, Gemini and Perplexity mock adapters and produced Research status
`COMPLETED`, visibility `89.94`, three responses, three extracted entity observations, three sources
and a one-node deduplicated graph.

## New API operations

- `GET/POST /prompts`
- `GET/PATCH /prompts/{id}`
- `POST /prompts/{id}/clone`
- `POST /prompts/{id}/activate`
- `POST /prompts/{id}/deprecate`
- `GET /research/templates`
- `GET /research/templates/{code}`
- `POST /research/wizard/review`
- `POST /research/wizard/run`
- `GET /research/{id}/final-report`

OpenAPI now exposes 145 paths and 180 operations; contract validation passes.

## Persistence and migration

Alembic revision `0042` adds `prompt_definitions` and `research_template_definitions`, uniqueness
constraints, the category/language index and default catalogs. Isolated `0041 → 0042 → 0041 →
0042` passes locally. The complete PostgreSQL migration cycle is enforced by GitHub Actions.

## Main changed files

- Product module: `product/models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`.
- Migration: `backend/alembic/versions/0042_add_product_catalogs.py`.
- Integration: `backend/app/main.py`, `backend/alembic/env.py`, `research/service.py`.
- Providers: `backend/app/providers/provider.py`, `transport.py`.
- Demo: `scripts/run_skinjestique_demo.py`.
- Tests: `tests/test_first_real_product.py`, `tests/test_provider_readiness.py`.
- Documentation: `README.md`, `FIRST_RESEARCH.md`, `docs/architecture.md`, `docs/UserGuide.md`,
  `docs/Roadmap.md`.

## Validation results

| Check | Result |
|---|---|
| Ruff | PASS |
| Pytest | 219 PASS |
| Compileall | PASS |
| OpenAPI | PASS — 145 paths / 180 operations |
| Pipeline validation | PASS |
| Compatibility validation | PASS |
| Sprint migration upgrade/downgrade | PASS |
| Skinjestique E2E demo | PASS |
| Provider contract matrix | PASS |
| Docker build/runtime | Pending authoritative PR CI |
| PostgreSQL full migration cycle | Pending authoritative PR CI |

## Architecture and compatibility

The product layer owns orchestration, not metric logic. Existing engines remain authoritative and
are accessed through their public services/ports. No existing route or schema was removed. The
stable `local` provider identifier was retained for Ollama compatibility. No new runtime dependency
or cyclic domain import was introduced.

Performance targets adopted for the closed MVP are API p50 ≤ 250 ms, p95 ≤ 1 s and p99 ≤ 2 s
excluding provider latency; mobile LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1; API SLO 99.5%.

## Known limitations

- Wizard execution is synchronous. Async progress streaming is intentionally deferred until after
  architecture review.
- Real provider credentials were not used; adapters are production-shaped and the reproducible
  acceptance scenario uses deterministic mock mode.
- The report is JSON/API-first; a dedicated visual web client is outside Sprint 10.
- Fresh SQLite migration from revision zero remains blocked by the pre-existing revision `0012`
  constraint-alter limitation. Sprint `0042` itself is reversible on SQLite, while PostgreSQL is the
  supported production migration target.
