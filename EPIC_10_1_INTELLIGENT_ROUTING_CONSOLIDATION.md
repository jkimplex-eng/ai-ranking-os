# EPIC 10.1 — Intelligent Routing Consolidation

Status: validation in progress on `feature/epic-10.1-intelligent-routing-consolidation`.

## Result

All platform LLM execution now crosses the public `LLMRouterPort`. Research, model benchmarking,
and empirical model evaluation no longer instantiate providers. The composition root connects the
Router to provider infrastructure, while routing decisions depend only on readiness and evaluation
ports.

The canonical execution path is:

`Domain -> LLMRouterPort -> Policy -> Execution Plan -> Dispatcher -> Provider Adapter -> LLM`.

## Delivered tasks

| Task | Result |
|---|---|
| 1001 / 1008 | One route implementation; `route_from_config` and domain bypasses removed. |
| 1002 | FAST, BALANCED, HIGH_QUALITY, FREE, PRIVATE, ENTERPRISE profiles in API and UI. |
| 1003 | `ollama` is the only local-provider identifier; `local` remains input-only compatibility alias. |
| 1004 | Database registry is authoritative at runtime; YAML only bootstraps/upserts it. |
| 1005 | Executable Groq and GitHub Models OpenAI-compatible adapters registered. |
| 1006 / 1011 | READY, NOT_CONFIGURED, DISABLED, UNAVAILABLE readiness states filter routing plans. |
| 1007 | Atomic pre-execution budget reservation, hard rejection, release/settlement and actual-cost log. |
| 1009 | Readiness, model evaluation and Router ports separate policy from infrastructure. |
| 1010 | `POST /research/run` enqueues durable work; worker executes it; job status is readable. |

## API additions

- `GET /router/profiles`
- `PATCH /router/profiles/{profile}`
- `POST /research/run` (202)
- `GET /research/jobs/{job_id}`

Legacy synchronous research endpoints remain available for backward compatibility, but the new
product execution contract is the queued endpoint.

## Database

- `0052`: router budget reservations and canonical `local` -> `ollama` data migration.
- `0053`: durable asynchronous research jobs.

Both migrations define upgrade and downgrade paths. PostgreSQL execution evidence is recorded in
the staging section once the isolated deployment completes.

## Local validation

- Ruff: PASS.
- Compileall: PASS.
- Pytest: PASS (258 tests).
- Frontend ESLint, TypeScript and production build: PASS.
- Alembic graph: single head `0053`.

## Live-provider policy

No mock result is reported as a live validation. Providers without credentials remain
`NOT_CONFIGURED` and are excluded from routing. Ollama, Groq, GitHub Models, OpenAI and Gemini live
results are recorded separately; missing external credentials are an explicit blocked result, not
a fabricated pass.

## Known compatibility surface

- `ProviderFactory.create("local")` is retained only as an infrastructure-bound input alias and
  returns the canonical `ollama` adapter. It is never emitted by Registry, API, UI or Router.
- `POST /research/{id}/run` remains synchronous for existing clients. New work must use
  `POST /research/run` and poll `GET /research/jobs/{job_id}`.
