# TASK-1116 — Product Analytics

Status: implemented on `feature/epic-11-product-readiness`.

## Delivered

- Independent `product_analytics` bounded context using Repository, Service, DI,
  SQLAlchemy 2, and Pydantic v2.
- Normalized product event ingestion, batch ingestion, browser sessions, salted IP
  hashing, and failure-isolated HTTP instrumentation.
- DAU, WAU, MAU, retention, session/research/report timings, research success and
  failure rates, feedback/errors, leaders, prompt templates, provider usage,
  token, cost, latency, Visibility, and recommendation aggregates.
- Hourly/daily/weekly/monthly time buckets and organization, user, provider,
  template, region, language, and date filters.
- Five-minute materialized aggregate cache, batch event intake, and paginated
  event inspection.
- CSV, JSON, and XLSX export.
- Responsive Product Analytics UI with overview KPIs, usage chart, research
  health, providers, users, feedback, and error panels.
- System Admin and Organization Admin authorization through the public RBAC adapter.

## API

- `GET /product-analytics/dashboard`
- `POST /product-analytics/refresh`
- `POST /product-analytics/events/batch`
- `GET /product-analytics/events`
- `POST /product-analytics/sessions`
- `POST /product-analytics/sessions/{session_id}/finish`
- `GET /product-analytics/export/{format_name}`

## Persistence

Migration `0069_add_product_analytics` adds `product_analytics_events`,
`product_analytics_sessions`, and `product_analytics_reports`, including lookup
indexes and a fully reversible downgrade.

## Changed areas

`product_analytics/`, `backend/app/main.py`, `backend/alembic/env.py`, migration
`0069`, `rbac/beta_adapter.py`, `frontend/src/api.ts`, `frontend/src/main.tsx`,
`frontend/src/styles.css`, tests, README, and architecture documentation.

## Verification

- Ruff: PASS.
- Pytest: PASS, 276 tests.
- Compileall: PASS.
- TypeScript and ESLint: PASS.
- Frontend production build: PASS.
- Playwright: PASS (1 local test; production-only E2E correctly skipped without URL).
- OpenAPI: PASS, 216 paths including Product Analytics.
- Alembic 0069 PostgreSQL upgrade/downgrade SQL: PASS. The live PostgreSQL cycle
  and Docker runtime are executed by GitHub Actions.

## Known limitations

- Product analytics is first-party and intentionally does not provide cross-device
  identity stitching.
- Cache invalidation is time-based; forced refresh is available to administrators.
- Organization ownership enforcement relies on the current public RBAC adapter and
  can adopt tenant-scoped policies when Organization Management is implemented.
