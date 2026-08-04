# Benchmark Engine

TASK-703 compares entities through the public `AnalyticsDataSource`; the module imports neither
Research nor Graph. It supports AI Visibility, Recommendation, Mention, Citation, Coverage, and
Confidence.

Each immutable versioned snapshot contains per-metric values, competition ranks, percentiles,
population averages, deltas from average and leader, plus an overall score/rank/percentile.
Multiple observations per entity are averaged deterministically.

API:

- `POST /benchmarks`
- `GET /benchmarks`
- `GET /benchmarks/{id}`

