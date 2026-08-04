# Relationship Discovery

Relationship Discovery v1 consumes only the public `GraphProvider` and
`EvidenceProvider` contracts. The production evidence adapter reads Entity Extraction
through its provider interface; the core has no Research dependency.

Supported types are `MENTIONS`, `RECOMMENDS`, `REFERENCES`, `COMPETES_WITH`,
`RELATED_TO`, `BELONGS_TO`, `PRODUCES`, and `CREATED_BY`. Multiple independent
evidence records are combined as `1 - product(1 - confidence)`. Source identities
prevent duplicate evidence and candidate identity prevents duplicate runs.

Approval creates a derived immutable GraphSnapshot containing the typed edge.
Approval and rejection are retained in `RelationshipDecision` history.

- `POST /relationship-discovery/run`
- `GET /relationship-discovery/candidates`
- `POST /relationship-discovery/{candidate_id}/approve`
- `POST /relationship-discovery/{candidate_id}/reject`

