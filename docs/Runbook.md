# RC1 Runbook

## Router unavailable

Check `/system/router` and `/system/providers`. Restore at least one ACTIVE model
that satisfies required capabilities and context. If circuits are OPEN, inspect
provider errors; do not force-close until the provider is healthy.

## High error rate

Correlate `/router/history`, executor history, and provider metrics by
correlation ID. Disable the failing model or route through FALLBACK. Escalate
when the error budget is exhausted.

## Budget exhausted

Confirm `/system/costs`, then enable `cost-optimized`, reduce output limits, or
raise the reviewed policy budget. Cost downgrade is automatic once limits are
reached.

## Database failure

Stop mutations, verify PostgreSQL connectivity and storage, restore from the
latest backup/PITR, run Alembic to head, then validate counts and a canary route.
Target RPO is five minutes and RTO thirty minutes.

## Redis failure

The API reports degraded cache health. Restore Redis connectivity and verify
`/system/cache`; database-backed Router operations remain authoritative.

## Release verification

Run Ruff, Pytest with coverage, Alembic offline SQL generation, the validation
pipeline, `/system/health`, `/router/status`, and `/metrics`. Record the build
SHA and report timestamp in the release evidence.
