# Alert Engine

Alert Engine v1 evaluates significant changes between scored observations through
the read-only `AlertDataSource` port. Research-specific mapping is isolated in
`research_adapter.py`.

Versioned rules detect Visibility drops, UP/DOWN reversals, disappeared brand
recommendations or authoritative citations, new CRITICAL recommendations, and
sharp Confidence changes. Every detected alert receives an immutable `DETECTED`
event for audit and future notification delivery.

- `GET /entities/{id}/alerts` returns persisted history, newest first.
- `POST /entities/{id}/alerts/evaluate` evaluates and persists current changes.

Default v1 thresholds are 10 Visibility points and 15 Confidence points.

