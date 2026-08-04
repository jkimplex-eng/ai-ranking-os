# Influence Scoring

TASK-605 calculates deterministic influence metrics over the latest immutable Graph Engine
snapshot. The core depends only on the `GraphProvider` read port; `PublicGraphAdapter` is the
infrastructure boundary to Graph Engine.

Metrics are Degree, Weighted Degree, PageRank, Betweenness, Closeness, and a versioned composite
Influence Score (0–100). Version 1.0 weights are 20%, 20%, 25%, 15%, and 20% respectively.
Results are persisted once per graph snapshot and algorithm version.

Endpoints:

- `GET /graph/influence`
- `GET /graph/influence/{entity_id}`

