# Graph Search

TASK-604 provides read-only search over the latest immutable graph snapshot through a public
`GraphProvider` port. It supports names, canonical names, entity IDs, aliases, node and
relationship types, confidence filtering, pagination, and deterministic BFS traversal.

Endpoints:

- `GET /graph/search`
- `GET /graph/node/{id}`
- `GET /graph/neighbors/{id}` with `depth=1..5`

Multi-value filters use repeated query parameters, for example
`?node_type=Brand&node_type=Product`. Traversal direction is `OUTGOING`, `INCOMING`, or `BOTH`.

