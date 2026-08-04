# Baseline & Regression Detection

Baseline Engine v1 consumes the public `TrendDataSource` and has no dependency on
Research implementation details. A baseline snapshot captures Visibility, Mention,
Recommendation, Citation, Coverage, and Confidence scores.

Score-point declines are classified as `MINOR` (5), `MODERATE` (10), `MAJOR` (20),
or `CRITICAL` (30). Thresholds and algorithm version are persisted. Policies are
`MANUAL`, `LATEST`, and `BEST_VISIBILITY`; automatic updates happen after evaluation
so every RegressionEvent remains tied to the snapshot actually compared.

- `POST /entities/{id}/baseline`
- `GET /entities/{id}/baseline`
- `POST /entities/{id}/baseline/evaluate`

