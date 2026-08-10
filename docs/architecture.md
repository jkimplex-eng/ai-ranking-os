# AI Ranking OS Architecture

AI Ranking OS v1.0 RC1 is a modular FastAPI application backed by PostgreSQL 16
and Redis 8. The synchronous request path is Query Intent → LLM Router → Query
Executor → Entity Extraction → Reason Engine → AI Visibility → Knowledge Graph.
Correlation IDs and typed Pydantic v2 contracts cross every boundary.

## Sprint 10 product orchestration

The `product` module is the application layer for the first user journey. It
depends on public service and port contracts and orchestrates existing domains;
it does not reimplement their scoring or extraction logic. Its only owned
persistence is the versioned Prompt Library and read-only Research Template
catalog. Wizard state becomes an ordinary Research record, and downstream
artifacts are recorded in Research metadata for backward-compatible reporting.

Dependency direction remains `product -> public services/ports -> repositories
-> SQLAlchemy`. The final report is read-only composition: score, trend,
benchmark, insights, recommendations and graph values come from their owning
engines. Provider-specific payloads are normalized before extraction/scoring.

The production Router owns model selection. Its repository persists models,
policies, routing history, cost entries, and circuit state through SQLAlchemy 2.
YAML files provide bootstrapping and runtime defaults; database records are the
dynamic control plane. Execution plans use SINGLE, PARALLEL, ENSEMBLE, or
FALLBACK and are consumed directly by Query Executor.

Decision Center and Execution Engine manage work, agents, sprints, retries, and
long-running execution independently of the online query pipeline. Monitoring
aggregates both paths and exports Prometheus metrics.

State belongs in PostgreSQL, transient coordination in Redis, and configuration
in environment variables plus version-controlled YAML. API, worker, PostgreSQL,
and Redis are independently deployable containers.

RC1 targets 99.9% service availability. Router overhead objectives are p50 ≤50
ms, p95 ≤150 ms, and p99 ≤500 ms excluding provider latency. Recovery objectives
are RPO ≤5 minutes and RTO ≤30 minutes.
## Product Analytics bounded context

`product_analytics` is an independent telemetry bounded context. HTTP and domain
producers submit normalized `AnalyticsEvent` records through one service; the
module never imports Research models or UI components. Its repository owns the
append-only event stream, sessions, and materialized `AnalyticsReport` aggregates.
The engine computes usage, retention, operational research/report indicators,
provider consumption, feedback, errors, and time buckets. Cached aggregates avoid
replaying the complete event stream on every dashboard request.

```text
HTTP/domain producers -> ProductAnalyticsService -> AnalyticsEvent repository
                                             |-> aggregation engine
                                             |-> cached AnalyticsReport
                                             `-> dashboard/export API -> Web UI
```

Authorization is applied at the API adapter through the platform administrator
dependency. The core service and repository remain transport- and screen-neutral.
