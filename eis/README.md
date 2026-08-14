# EIS Scoring

Explainable heuristic estimate of a publication resource's relevance for AI visibility. Scores
are stored for a platform, optional frozen query, and AI engine. The response exposes measured
inputs, component values, weights, contributions, denominator, bias, caps, exclusions, evidence
status, and methodology versions. It distinguishes zero from missing or insufficient evidence and
never presents correlation as causation.

API:

- `POST /api/v1/eis/calculate`
- `POST /api/v1/eis/batch-prioritize`
- `GET /api/v1/eis/{score_id}`
- `GET /api/v1/eis/history/{platform_id}`
