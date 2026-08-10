# AI Ranking OS

> Intelligent Routing consolidation details and validation evidence are maintained in
> [EPIC_10_1_INTELLIGENT_ROUTING_CONSOLIDATION.md](EPIC_10_1_INTELLIGENT_ROUTING_CONSOLIDATION.md).

## Intelligent LLM Routing

The platform supports provider-independent routing across local, free-tier and paid models.
Configure `AI_ROUTING_MODE` (`LOCAL`, `HYBRID`, `CLOUD`) and `AI_HYBRID_ORDER` in the environment.
See [EPIC_10_INTELLIGENT_LLM_ROUTING.md](EPIC_10_INTELLIGENT_LLM_ROUTING.md) and
[Local AI Mode](docs/LOCAL_AI_MODE.md) for architecture and operations.

Production deployment assets are in `deployment/production`. The first isolated installation runs
on the audited VPS behind loopback port `8100`; see [First Deploy](docs/FIRST_DEPLOY.md),
[Deployment](docs/Deployment.md), and [Operations](docs/Operations.md). The existing
`разуммаркета.рф` landing and Ozon Agent are not part of this Compose project.

AI Ranking OS RC2.1 is a provider-neutral intelligence platform for ranking
research, decisioning, analytics, and knowledge workflows behind FastAPI.

The first-product workflow now lets a user select a brand, models, language,
region and versioned prompt, run the research, and receive a unified report.
For the reproducible Skinjestique demo, see [FIRST_RESEARCH.md](FIRST_RESEARCH.md):

```bash
python scripts/run_skinjestique_demo.py --output skinjestique-report.json
```

## Stack

- Python 3.13
- FastAPI, Pydantic v2, SQLAlchemy 2, and Alembic
- PostgreSQL 16 and Redis 8
- Docker Compose

## Quick start with Docker

Prerequisites: Docker Engine with Docker Compose v2.

```bash
git clone <repository-url> ai-ranking-os
cd ai-ranking-os
cp .env.example .env
docker compose up --build
```

The `.env` copy is optional for the default local configuration. Compose waits for
PostgreSQL and Redis, runs Alembic migrations, starts the API on
`http://localhost:8000`, and starts the worker.

Verify the API:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/version
```

Expected responses:

```json
{"status":"ok"}
{"version":"1.0.0"}
```

Stop the stack with `docker compose down`. To also remove local database and Redis
volumes, run `docker compose down --volumes`.

### Production process model

The Docker image starts two Uvicorn workers by default (`WEB_CONCURRENCY=2`) and uses
`exec`, so Uvicorn is PID 1 and receives `SIGTERM` directly. Compose grants a 40-second
stop window; the application uses a configurable 30-second graceful shutdown timeout.
The image has its own container `HEALTHCHECK` in addition to Compose probes.

Kubernetes manifests are in `infra/kubernetes`. They intentionally run one worker per pod
and two replicas: Kubernetes owns horizontal scaling, health isolation, rolling replacement,
and resource accounting. Database migrations run as a separate Job before rollout, preventing
multiple pods from racing on Alembic. Production requires `AUTH_JWT_SECRET`, `DATABASE_URL`,
and `REDIS_URL` through the referenced Secret.

Redis is deliberately not a Compose startup dependency for API or worker. Cache operations
fail open to bounded process memory, and the worker keeps retrying Redis heartbeats. PostgreSQL
remains readiness-critical. SQLAlchemy uses pre-ping, connection recycling, bounded overflow,
and pool acquisition timeouts configured through `DATABASE_POOL_*` variables.

## Local development

Prerequisites: Python 3.13 and running PostgreSQL/Redis instances.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload
```

Production images and CI install the committed `requirements.lock` and
`requirements-dev.lock`. Regenerate them from the human-maintained input files with
`pip-compile --strip-extras requirements.txt` and the equivalent development command.

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1` and copy the environment file with
`Copy-Item .env.example .env`.

Run quality checks:

```bash
ruff check .
pytest
docker compose config
docker build -t ai-ranking-os:local .
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Process liveness; returns HTTP 200 when the API is running |
| `GET` | `/version` | Application semantic version |
| `GET` | `/docs` | Interactive OpenAPI documentation |
| `GET` / `POST` | `/tasks` | List and create Decision Center tasks |
| `GET` / `PATCH` | `/tasks/{id}` | Read and update a task |
| `POST` | `/tasks/{id}/assign` | Assign the task's single owner |
| `POST` | `/tasks/{id}/complete` | Complete a task after review |
| `GET` / `POST` | `/agents` | List and create agents |
| `GET` / `POST` | `/sprints` | List and create sprints |
| `GET` | `/queue` | READY tasks ordered by priority |
| `POST` | `/execution/start` | Schedule and run the next compatible task |
| `POST` | `/execution/cancel` | Cancel an active execution and requeue its task |
| `GET` | `/execution/{id}` | Read execution state, timings, result, and error |
| `GET` | `/execution/history` | List execution history |
| `POST` | `/visibility/calculate` | Calculate and persist one AI Visibility score |
| `POST` | `/visibility/batch` | Calculate and persist up to 100 scores |
| `GET` | `/visibility/{entity_id}` | Get the latest calculation for an entity |
| `POST` | `/entity-extraction/extract` | Extract entities and relations from one LLM response |
| `POST` | `/entity-extraction/batch` | Extract up to 100 LLM responses |
| `GET` | `/entity-extraction/{response_id}` | Get a stored extraction result |
| `POST` | `/intent/classify` | Classify one query and persist routing metadata |
| `POST` | `/intent/batch` | Classify up to 100 queries |
| `GET` | `/intent/{request_id}` | Get a stored intent classification |
| `POST` | `/executor/run` | Execute a Router Execution Plan |
| `POST` | `/executor/stream` | Execute a plan and return NDJSON events |
| `GET` | `/executor/{execution_id}` | Get a stored executor result |
| `POST` | `/executor/{execution_id}/cancel` | Request cooperative cancellation |
| `POST` | `/router/route` | Select models and build a production execution plan |
| `GET` / `POST` | `/router/models` | Search or dynamically register models |
| `GET` / `PATCH` / `DELETE` | `/router/model/{id}` | Read, update, or delete a model |
| `GET` | `/system/status` | Aggregated production component status |
| `GET` | `/system/metrics` | JSON operational metrics |
| `GET` | `/metrics` | Prometheus exposition endpoint |
| `GET` / `POST` | `/researches` | List and create research records |
| `GET` / `PATCH` / `DELETE` | `/researches/{id}` | Research CRUD |
| `GET` / `POST` | `/research-tasks` | List and create research tasks |
| `GET` / `PATCH` / `DELETE` | `/research-tasks/{id}` | Research task CRUD |
| `GET` / `POST` | `/responses` | List and create provider responses |
| `GET` / `PATCH` / `DELETE` | `/responses/{id}` | Research response CRUD |
| `GET` / `POST` | `/responses/{id}/extraction` | Read or rerun intelligence extraction |
| `GET` / `POST` | `/research` | Canonical Research API: list and create |
| `GET` / `PATCH` / `DELETE` | `/research/{id}` | Canonical Research CRUD |
| `POST` | `/research/{id}/run` | Execute one ResearchTask per selected model |
| `GET` / `POST` | `/research/{id}/score` | Read or recalculate AI Visibility Score v1 |
| `GET` | `/research/{id}/report` | Aggregate the complete persisted research result |
| `GET` | `/research/compare?left={id}&right={id}` | Compare two persisted research results |
| `GET` | `/research/history?entity_id={uuid}` | Paginated Research history and aggregates |
| `GET` / `POST` | `/research/{id}/recommendations` | Read or generate rule-based actions |
| `GET` | `/recommendation/templates` | List versioned action templates |
| `GET` | `/recommendation/templates/{code}` | Get the latest template version |
| `GET` | `/research/{id}/action-plan` | Assemble the latest actionable plan |
| `POST` | `/research/{id}/simulate` | Create deterministic impact forecasts |
| `GET` | `/research/{id}/simulation` | Read the latest saved forecast set |
| `GET` | `/entities/{id}/trend` | Build and persist all AI Visibility metric trends |
| `GET` | `/entities/{id}/trend/{metric}` | Build and return one metric trend |
| `GET` | `/entities/{id}/alerts` | Read persisted significant-change alerts |
| `POST` | `/entities/{id}/alerts/evaluate` | Evaluate versioned alert rules |
| `GET` / `POST` | `/schedules` | List or create recurring research schedules |
| `PATCH` / `DELETE` | `/schedules/{id}` | Update, enable, disable, or delete a schedule |
| `POST` | `/schedules/run` | Claim and execute all currently due schedules |
| `GET` / `POST` | `/entities/{id}/baseline` | Read or establish a quality baseline |
| `POST` | `/entities/{id}/baseline/evaluate` | Detect metric regressions against baseline |
| `POST` | `/graph/build` | Build an immutable versioned knowledge graph snapshot |
| `GET` | `/graph` | Read the latest graph snapshot |
| `GET` | `/graph/{snapshot_id}` | Read a specific graph snapshot |
| `POST` | `/entity-linking/run` | Resolve graph nodes to canonical entities |
| `GET` | `/entity-linking/candidates` | List and filter entity link candidates |
| `POST` | `/entity-linking/{candidate_id}/approve` | Manually approve a proposed link |
| `POST` | `/entity-linking/{candidate_id}/reject` | Manually reject a proposed link |
| `POST` | `/relationship-discovery/run` | Discover relationship candidates from evidence |
| `GET` | `/relationship-discovery/candidates` | List relationship candidates and evidence |
| `POST` | `/relationship-discovery/{candidate_id}/approve` | Approve and integrate a relationship |
| `POST` | `/relationship-discovery/{candidate_id}/reject` | Reject a relationship candidate |
| `GET` | `/graph/influence` | Rank entities using versioned graph influence metrics |
| `GET` | `/graph/influence/{entity_id}` | Get influence metrics for one entity |
| `GET` | `/graph/search` | Search graph nodes, aliases, types, and relationships |
| `GET` | `/graph/node/{entity_id}` | Get one graph node by internal or external ID |
| `GET` | `/graph/neighbors/{id}` | Traverse graph neighbors with bounded BFS |
| `POST` | `/analytics/query` | Execute filtered, grouped aggregate analytics |
| `GET` | `/analytics/runs` | List persisted analytics runs |
| `GET` | `/analytics/runs/{id}` | Get a reproducible analytics result |
| `GET` | `/segments/types` | List built-in and custom segment types |
| `POST` | `/segments` | Create a versioned segment definition |
| `GET` | `/segments` | List segment definitions |
| `POST` | `/segments/{id}/evaluate` | Evaluate and persist segment membership |
| `GET` | `/segments/{id}/memberships` | Read the latest membership snapshot |
| `POST` | `/benchmarks` | Compare entities across ranking metrics |
| `GET` | `/benchmarks` | List persisted benchmark snapshots |
| `GET` | `/benchmarks/{id}` | Get rankings, percentiles, and comparative analysis |
| `POST` | `/exports` | Stream filtered analytics as CSV, XLSX, JSON, or Parquet |
| `POST` | `/insights/generate` | Generate deterministic analytical insights |
| `GET` | `/insights/runs` | List persisted insight snapshots |
| `GET` | `/insights/runs/{id}` | Get growth, decline, anomaly, leader, and recommendation insights |

Decision Center enforces one owner per task, no more than one `IN_PROGRESS`
task per agent, and the mandatory `REVIEW` gate before `DONE`. Every mutation
is recorded atomically in `execution_logs`.

The Execution Engine schedules `HIGH` before `MEDIUM` before `LOW`, matches task
specialization to an idle enabled agent, and enforces one active execution per
task and agent. Codex, Qwen, and DeepSeek adapters are active; Claude and Gemini
are reserved. A failed adapter call is retried up to three times with exponential
backoff before the execution becomes `FAILED`.

Research runs invoke the selected provider/model through the Execution Engine
and persist one response for every terminal execution, including failures.
Provider-specific results are normalized to `content`, `citations`,
`finish_reason`, `usage`, and `metadata`; raw payloads, token usage, cost,
latency, and typed errors remain available for audit and diagnostics.
Every normalized response is then processed by a provider-independent extraction
service. Entities, brands, products, organizations, people, citations, and
recommendations are persisted against the response, whose processing status
becomes `PROCESSED` or `FAILED`.
When all expected responses reach a terminal processing status, Scoring Engine
v1 automatically persists mention, recommendation, citation, coverage,
confidence, and combined visibility scores. The `version` field keeps future
formula revisions backward compatible.
The Reporting API is a read-only composition layer: it returns research,
the latest score, responses, entities, citations, and recommendations without
triggering execution, extraction, or scoring.
Research Comparison is also read-only. It calculates `right − left` deltas for
all Scoring Engine v1 metrics and identifies new/disappeared entities and
recommendations using normalized, case-insensitive identities.
Research History groups explicitly linked researches by the indexed
`Research.entity_id` UUID. It returns newest-first rows, pagination metadata,
and best/latest/average/change aggregates without mutating research state.
Trend Engine consumes that score history through a public read port and persists
versioned snapshots for visibility, mention, recommendation, citation, coverage,
and confidence. Version 1 includes a three-point trailing moving average,
adjacent percentage changes, and `UP`, `DOWN`, or `STABLE` direction.
Alert Engine consumes score and intelligence history through a read-only port.
Versioned v1 rules detect material Visibility and Confidence changes, trend
reversals, disappeared recommendations or authoritative citations, and newly
created critical recommendations. Every detection is retained as an audit event.
Scheduled Research supports hourly, daily, weekly, monthly, and five-field cron
plans in UTC. Each run clones a Research template through a public launcher port,
prevents concurrent executions with row locking and a partial unique index, and
records every exponentially delayed retry in immutable execution history.
Baseline Engine compares the latest scored observation with a versioned snapshot
across all six visibility metrics. It persists classified regression events and
supports manual, latest-observation, and best-Visibility update policies.
Graph Engine consumes entities and typed relationships through public provider
ports, deduplicates stable external IDs, and persists immutable versioned snapshots.
The extraction adapter is isolated from the graph domain and can be replaced or
combined with future providers without changing Graph Engine.
Entity Linking normalizes Unicode, case, punctuation, and whitespace before matching.
Exact canonical and alias matches are automatic; uncertain fuzzy matches remain
pending for manual approval or rejection, with every decision retained for audit.
Relationship Discovery combines independent evidence with deterministic confidence,
deduplicates candidates, and integrates approved typed relationships by deriving a
new immutable graph snapshot.

Recommendation Engine v1 is a separate rule-based module. It consumes score
snapshots through a protocol-based adapter and persists versioned rules,
executions, and prioritized actions without importing Research in its core.
Each generated recommendation is pinned to a concrete template version. The
read-only Action Plan combines the recommendation, ordered steps, expected
result, and estimated execution time without regenerating recommendations.
Impact Simulator v1 applies rule thresholds and Scoring v1 weights without an
LLM. It stores an isolated forecast for every recommendation, including current
and predicted Visibility, expected metric change, confidence range, duration,
and model version.

The AI Visibility Engine accepts an entity plus per-model observations and
calculates mention frequency, recommendation position, citation count and
authority, cross-model presence, consistency, entity confidence, and freshness.
Weights are persisted and versioned; version `1.0` is installed by migration
`0004`. Input adapters accept `observations`, `responses`, `model_results`, or
an `entity_extraction_result` wrapper.

The Entity Extraction Engine accepts raw text or structured LLM output and
returns schema version `1.0` with entities, relations, resolution logs, confidence
scores, and deterministic knowledge graph IDs. It supports 16 entity types and
27 relation types. The pipeline performs extraction, relation detection,
deduplication, alias resolution, ambiguity handling, and knowledge graph mapping.
Entity, relation, run, and resolution history are persisted.

The Query Intent Engine detects language, extracts entities and constraints,
combines deterministic rule and hashing-embedding classifiers, supports
multi-intent results, and derives an expected output contract. Ten primary
intent classes and their subtype taxonomy are exposed through schema version
`1.0`. Low-confidence or ambiguous queries are marked for LLM fallback; a
provider-neutral fallback interface is available without requiring an external
model in local development.

The Query Executor accepts direct plans or an `execution_plan` Router wrapper.
It supports `SINGLE`, `PARALLEL`, `ENSEMBLE`, and `FALLBACK` strategies with
per-provider retries, exponential backoff, timeouts, cooperative cancellation,
NDJSON streaming, and telemetry hooks. Execution, latency, failure, and provider
metrics are persisted by migration `0007`.

The end-to-end validation harness exercises Query → Intent → production Router
→ Executor → Entity Extraction → Reason → Visibility → Knowledge Graph →
Response. The pipeline contains no compatibility adapters. Run validation and
generate reports with:

```bash
python -m validation.pipeline_validator --output validation_reports
```

Generated artifacts include an HTML report, JSON report, pipeline coverage
report, code coverage report, and producer/consumer compatibility matrix.

Example:

```json
{
  "entity_id": "skinjestique",
  "entity": "Skinjestique",
  "observations": [
    {
      "model": "qwen",
      "mentioned": true,
      "recommendation_position": 2,
      "citations": [{"source": "example.org", "authority": 0.8}],
      "entity_confidence": 0.92,
      "observed_at": "2026-07-29T12:00:00Z"
    }
  ]
}
```

## Database migrations

Apply all migrations:

```bash
alembic -c backend/alembic.ini upgrade head
```

Create a migration after changing SQLAlchemy models:

```bash
alembic -c backend/alembic.ini revision --autogenerate -m "describe change"
```

## Repository layout

- `backend/` — FastAPI service, worker, database models, and migrations
- `frontend/` — future web user interface
- `decision_center/` — ranking decisions and orchestration
- `execution_engine/` — priority queue, scheduler, worker adapters, retries, and history
- `ai_visibility/` — metric calculation, normalization, weights, confidence, and pipeline
- `entity_extraction/` — entity/relation extraction and knowledge graph resolution
- `influence/` — versioned graph centrality metrics and composite influence scoring
- `graph_search/` — filtered graph lookup, pagination, and bounded BFS traversal
- `query_intent/` — multilingual intent classification, constraints, and routing
- `query_executor/` — provider dispatch, parallelism, retries, streaming, and telemetry
- `backend/app/llm_router/` — registry, scoring, policies, plans, budgets, and circuits
- `providers/` — legacy import compatibility for RC1 provider clients
- `backend/app/providers/` — live/mock multi-provider transport, credentials,
  capabilities, pricing, limits, cache, health, metrics, and regional adapters
- `config/` — hot-reloaded router, provider, policy, and monitoring settings
- `reason_engine/` / `knowledge_graph/` — production pipeline stages
- `validation/` — E2E contracts, benchmarks, load tests, and report generation
- `validation_reports/` — generated validation, coverage, and compatibility artifacts
- `research/` — experiments and evaluation
- `analytics/` — provider-neutral aggregates, filters, grouping, intervals, and statistics
- `segmentation/` — built-in and custom rule-based analytical segments
- `benchmark/` — comparative rankings, percentiles, and metric deltas
- `export_engine/` — streaming CSV, XLSX, JSON, and Parquet exports
- `insights/` — deterministic growth, decline, anomaly, leader, and recommendation detection
- `product_analytics/` — privacy-aware product events, sessions, cached aggregates,
  dashboard metrics, filters, and CSV/JSON/XLSX exports
- `notification_center/` — categorized in-app inbox plus email, Telegram, and
  webhook delivery outbox with read state, archive, priorities, and pagination
- `organization_workspace/` — organization profiles, membership, invitations,
  roles, project links, limits, switching, and activity history
- `knowledge/` — retrieval assets and taxonomies
- `infra/` — deployment and infrastructure definitions
- `docs/` — architecture and operating documentation
- `tests/` — automated tests

## Product Analytics

System and organization administrators can open **Product Analytics** in the
application or request `GET /product-analytics/dashboard`. The dashboard supports
hourly, daily, weekly, and monthly periods plus organization, user, provider,
template, region, language, and date filters. Raw IP addresses are never stored;
the request instrumentation persists only a salted hash. Exports are available at
`GET /product-analytics/export/{format_name}` for `csv`, `json`, and `xlsx`.
