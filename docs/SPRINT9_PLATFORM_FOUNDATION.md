# Sprint 9 — Platform Foundation

## Result

TASK-801 through TASK-808 are implemented. Alembic head is `0040`.

| Task | Module | Status |
|---|---|---|
| 801 Authentication | `authentication` | PASS |
| 802 RBAC | `rbac` | PASS |
| 803 API Keys | `apikeys` | PASS |
| 804 Audit Log | `audit` | PASS |
| 805 Observability | `observability` | PASS |
| 806 Cache Layer | `cache` | PASS |
| 807 Rate Limiter | `rate_limit` | PASS |
| 808 Production Hardening | `hardening` | PASS |

## Delivered

- 8 independent modules, 8 reversible Alembic revisions, and 35 new API operations.
- JWT access/refresh tokens, Argon2, rotation, revocation, replay detection and sessions.
- Resource/action/scope RBAC, custom roles, multiple inheritance and cycle prevention.
- One-time API-key secrets, scopes, expiration, rotation, revocation and rate plans.
- Immutable append-only audit records with filtering and CSV export.
- Prometheus compatibility, readiness/liveness/health ports and trace-span storage.
- Redis/memory cache adapters with TTL, tags, warming and read/write-through behavior.
- Token-bucket and sliding-window limiting with burst and Retry-After decisions.
- Idempotency/DLQ storage and reusable circuit-breaker, retry, timeout and backpressure controls.

## Public ports

`AuthPrincipal`, `IdentityProvider`, `AuthorizationProvider`, `ApiKeyValidator`,
`AuditWriter`, `HealthCheck`, `MetricsProvider`, `CacheBackend`, `RateLimitProvider`,
`DeadLetterQueue`, and `FailoverProvider`.

## Validation

- Tests: 202 passed; 16 new Sprint 9 tests.
- Platform module coverage: 84%.
- Ruff and compileall: PASS.
- OpenAPI: 135 paths, 168 operations; 35 Sprint 9 operations.
- Pipeline validation: 16/16 PASS; compatibility matrix: 8/8 PASS.
- Pipeline contract/stage coverage: 100%.
- Secret scan: 0 critical/high findings.
- Offline dependency scan: no detected vulnerability findings.
- PostgreSQL upgrade/downgrade SQL: PASS for revisions 0033–0040.

## Architecture

Platform modules own their persistence and expose public ports. RBAC stores opaque user IDs
and does not import Authentication models. Cache, rate limiting, audit, observability and
hardening do not import Research or Graph internals. Existing public APIs remain unchanged.

## Known limitations

- Live PostgreSQL and Redis services were unavailable in the local environment; PostgreSQL
  migrations were dialect-compiled in both directions and isolated migrations were executed
  against SQLite. Redis has a production adapter, while deterministic tests use memory.
- OAuth2/OpenID Connect providers are extension ports only, as required.
- Rate-limit policies are opt-in; no default policy throttles legacy endpoints.
- Distributed trace export and cross-node rate-limit atomicity require deployment adapters.
- The existing TestClient dependency emits one upstream Starlette/httpx2 deprecation warning.

## Before Sprint 10

Run the generated SQL against staging PostgreSQL, exercise Redis failover, configure production
JWT secrets and default RBAC/rate-limit policies, then add SDK contract tests generated from the
current OpenAPI document.
