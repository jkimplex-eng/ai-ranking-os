# Trend Engine

`TrendEngine` builds deterministic, versioned time-series snapshots for an entity.
The domain consumes only `TrendDataSource`; `research_adapter.py` is the integration
boundary that supplies scored observations.

Version 1 uses a three-observation trailing moving average. Adjacent changes within
one score point are `STABLE`; larger positive or negative changes are `UP` or `DOWN`.
Percentage change is omitted for the first point and after a zero-valued point because
the relative change is undefined.

Endpoints:

- `GET /entities/{id}/trend`
- `GET /entities/{id}/trend/{metric}` where metric is `visibility`, `mention`,
  `recommendation`, `citation`, `coverage`, or `confidence`.

Each request builds and persists a new immutable snapshot for auditability.

