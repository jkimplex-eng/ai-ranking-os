# EPIC 10.1 — Intelligent Routing Consolidation

Status: implementation complete; Release Gate №2 evidence recorded on
`feature/epic-10.1-intelligent-routing-consolidation`.

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
- Pytest: PASS (259 tests).
- Frontend ESLint, TypeScript and production build: PASS.
- Alembic graph: single head `0053`.

## Isolated staging validation

Staging runs at `/opt/ai-ranking-os-staging-epic101` as Compose project
`ai-ranking-os-staging-epic101` on `127.0.0.1:18100`. Production project, volumes and port 8100
were not reused. PostgreSQL executed the full upgrade to `0053`, downgrade to `0051`, and upgrade
back to `0053` successfully.

The host Ollama service binds loopback only. Staging therefore uses a relay bound exclusively to
the Docker bridge (`172.17.0.1:11435 -> 127.0.0.1:11434`); it is not internet-exposed.

### Real Skinjestique/Ollama evidence

| Scenario | Result |
|---|---|
| Single PRIVATE research | PASS, 12.42–19.41 seconds end-to-end |
| 20 concurrent enqueues | PASS, 20/20; enqueue 0.403 s; total 242.675 s; 0.082 research/s |
| 50 concurrent enqueues | PASS, 50/50; enqueue 1.035 s; total 667.156 s; 0.075 research/s |
| Redis stopped | PASS, research completed in 15.363 s via durable PostgreSQL queue |
| Ollama relay stopped | PASS, provider became UNAVAILABLE and queued research became FAILED |
| Ollama recovery | PASS, UNAVAILABLE -> READY and subsequent research COMPLETED |

Across the valid 1+20+50 live run, 71 Ollama responses were stored: average provider latency
11,781.79 ms (min 5,942; max 18,975), 9,010 total tokens and USD 0 cost. The live model was
`qwen2.5:3b`; a sample answer correctly stated that Skinjestique has limited mainstream AI
visibility. This is a basic relevance check, not a formal answer-quality benchmark.

The current single worker deliberately applies backpressure. It preserves all jobs but caps live
Ollama throughput near 0.08 research/s; horizontal workers and provider-specific concurrency limits
are recommended before production traffic above this level.

### External providers

OpenAI, Gemini, Groq and GitHub Models credentials are absent on staging. Their live tests are
therefore **BLOCKED**, not mocked or reported as PASS. Registry exposes each as `NOT_CONFIGURED`,
and Router excludes it before plan/failover construction. Their adapters remain covered by the
provider contract tests in mock mode.

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
- The Ollama bridge relay is staging infrastructure necessitated by the VPS service binding only
  `127.0.0.1`; production should use an explicit private network listener or a managed sidecar.
