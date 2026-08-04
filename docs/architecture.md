# AI Ranking OS Architecture

AI Ranking OS v1.0 RC1 is a modular FastAPI application backed by PostgreSQL 16
and Redis 8. The synchronous request path is Query Intent → LLM Router → Query
Executor → Entity Extraction → Reason Engine → AI Visibility → Knowledge Graph.
Correlation IDs and typed Pydantic v2 contracts cross every boundary.

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
