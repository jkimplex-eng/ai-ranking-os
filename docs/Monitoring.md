# Monitoring

JSON operational views are available below `/system`: `health`, `status`,
`providers`, `router`, `pipeline`, `metrics`, `version`, `costs`, `cache`, and
`build`. `GET /metrics` exposes Prometheus text format.

Metrics cover HTTP traffic and latency, routing selection and score, cost,
fallbacks, errors, circuits, queue depth, pipeline validation, tokens, and
component record counts. Prometheus should scrape `/metrics` every 15 seconds.

RC2.1 adds provider request throughput, latency, errors by normalized category,
timeouts, retries, in-flight concurrency, availability, cache hits/misses,
prompt/completion tokens, and cost by provider/model/currency.

Recommended alerts:

- API error ratio above 1% for five minutes.
- p95 HTTP or router latency above the configured SLO for ten minutes.
- no ACTIVE route or all candidate circuits OPEN.
- pipeline validation not healthy.
- daily or monthly budget at 80% and 100%.
- READY queue growing for fifteen minutes.
- PostgreSQL unhealthy; Redis degraded is warning-level until a cached workflow
  is required.
