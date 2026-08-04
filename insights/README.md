# Insights Engine

TASK-705 turns public analytics observations into deterministic conclusions without an LLM. The
module imports neither Research nor Graph and consumes only `AnalyticsDataSource`.

Version 1.0 detects growth, decline, z-score anomalies, leaders, and key changes. Fixed metric
rules produce actionable recommendations for Visibility, Mention, Recommendation, Citation,
Coverage, and Confidence. Runs and evidence are persisted as immutable snapshots.

API:

- `POST /insights/generate`
- `GET /insights/runs`
- `GET /insights/runs/{id}`

