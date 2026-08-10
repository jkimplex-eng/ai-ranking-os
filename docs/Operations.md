# Production Operations

Use `docker compose --env-file .env -f docker-compose.yml ps` for service state and `logs --since
30m` for JSON logs. `/live` proves the process is running; `/ready` requires PostgreSQL and reports
Redis as healthy or degraded; `/metrics` exports Prometheus data. `/system/status`,
`/system/providers`, `/system/costs`, and `/system/resources` require authentication.

Alerts should cover readiness failures, repeated restarts, disk above 80%, database backup age,
queue growth, provider errors and sustained latency. Redis loss is degraded mode: API and database
operations remain available, while cache, queue acceleration and worker heartbeats are impaired.

Daily routine: verify container health, backup freshness, disk capacity, certificate expiry and
provider availability. Keep ports 5432, 6379 and 8000 private.
