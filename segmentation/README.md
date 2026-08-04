# Segmentation

TASK-702 provides extensible, rule-based segmentation over the public `AnalyticsDataSource` port.
The module does not import Research or Graph. Built-in types are Brand, Category, Country,
Marketplace, Source, Language, and Model; `CUSTOM` combines arbitrary dimension and metric rules.

Definitions are versioned. Every evaluation creates an immutable snapshot with deterministic
member keys, source/match counts, dimensions, metrics, and observation timestamps.

API:

- `GET /segments/types`
- `POST /segments`, `GET /segments`
- `GET`, `PATCH`, `DELETE /segments/{id}`
- `POST /segments/{id}/evaluate`
- `GET /segments/{id}/memberships`

