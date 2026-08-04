CREATE TABLE canonical_entities (
 id INTEGER PRIMARY KEY, canonical_name VARCHAR(500) NOT NULL,
 normalized_name VARCHAR(500) NOT NULL, entity_type VARCHAR(100) NOT NULL,
 algorithm_version VARCHAR(50) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 updated_at TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX uq_canonical_entities_type_normalized
 ON canonical_entities (entity_type, normalized_name);
CREATE TABLE entity_aliases (
 id INTEGER PRIMARY KEY,
 canonical_entity_id INTEGER NOT NULL REFERENCES canonical_entities(id) ON DELETE CASCADE,
 alias VARCHAR(500) NOT NULL, normalized_alias VARCHAR(500) NOT NULL,
 entity_type VARCHAR(100) NOT NULL, source VARCHAR(50) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX uq_entity_aliases_type_normalized
 ON entity_aliases (entity_type, normalized_alias);
CREATE INDEX ix_entity_aliases_canonical_id ON entity_aliases (canonical_entity_id);
CREATE TABLE link_candidates (
 id INTEGER PRIMARY KEY, graph_snapshot_id INTEGER NOT NULL,
 graph_node_id INTEGER NOT NULL, external_id VARCHAR(300) NOT NULL,
 entity_name VARCHAR(500) NOT NULL, normalized_name VARCHAR(500) NOT NULL,
 entity_type VARCHAR(100) NOT NULL,
 canonical_entity_id INTEGER REFERENCES canonical_entities(id) ON DELETE SET NULL,
 confidence DOUBLE PRECISION NOT NULL, match_method VARCHAR(50) NOT NULL,
 status VARCHAR(20) NOT NULL, algorithm_version VARCHAR(50) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL, resolved_at TIMESTAMPTZ
);
CREATE INDEX ix_link_candidates_status_created ON link_candidates (status, created_at);
CREATE INDEX ix_link_candidates_snapshot_node ON link_candidates (graph_snapshot_id, graph_node_id);
CREATE TABLE link_decisions (
 id INTEGER PRIMARY KEY,
 candidate_id INTEGER NOT NULL REFERENCES link_candidates(id) ON DELETE CASCADE,
 decision VARCHAR(30) NOT NULL, canonical_entity_id INTEGER,
 actor VARCHAR(100) NOT NULL, reason TEXT, algorithm_version VARCHAR(50) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_link_decisions_candidate_created ON link_decisions (candidate_id, created_at);

