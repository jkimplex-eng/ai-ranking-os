# Graph Engine

Graph Engine v1 builds immutable knowledge graph snapshots from the public
`EntityProvider` and `RelationshipProvider` interfaces. The engine has no dependency
on Research or Entity Extraction implementations; `extraction_adapter.py` is an
infrastructure adapter for existing extraction history.

Node types are extensible strings and currently include values such as `Brand`,
`Product`, `Organization`, `Person`, and `Source`. Edges are typed strings such as
`PRODUCES`, `OWNS`, `MENTIONS`, or any future relationship type.

Each build deduplicates nodes by stable external ID, removes dangling edges,
deduplicates typed edges, and persists a new snapshot with structure version `1.0`.

- `POST /graph/build`
- `GET /graph`
- `GET /graph/{snapshot_id}`

