CREATE TABLE relationship_candidates (
 id INTEGER PRIMARY KEY, graph_snapshot_id INTEGER NOT NULL,
 source_external_id VARCHAR(300) NOT NULL, target_external_id VARCHAR(300) NOT NULL,
 relationship_type VARCHAR(30) NOT NULL, confidence DOUBLE PRECISION NOT NULL,
 status VARCHAR(20) NOT NULL, algorithm_version VARCHAR(50) NOT NULL,
 integrated_snapshot_id INTEGER, created_at TIMESTAMPTZ NOT NULL,
 resolved_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX uq_relationship_candidates_identity ON relationship_candidates
 (graph_snapshot_id, source_external_id, target_external_id, relationship_type);
CREATE INDEX ix_relationship_candidates_status_created
 ON relationship_candidates (status, created_at);
CREATE TABLE relationship_evidence (
 id INTEGER PRIMARY KEY,
 candidate_id INTEGER NOT NULL REFERENCES relationship_candidates(id) ON DELETE CASCADE,
 source_type VARCHAR(100) NOT NULL, source_reference VARCHAR(300) NOT NULL,
 confidence DOUBLE PRECISION NOT NULL, payload JSON NOT NULL,
 created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_relationship_evidence_candidate ON relationship_evidence (candidate_id);
CREATE UNIQUE INDEX uq_relationship_evidence_source ON relationship_evidence
 (candidate_id, source_type, source_reference);
CREATE TABLE relationship_decisions (
 id INTEGER PRIMARY KEY,
 candidate_id INTEGER NOT NULL REFERENCES relationship_candidates(id) ON DELETE CASCADE,
 decision VARCHAR(20) NOT NULL, actor VARCHAR(100) NOT NULL, reason TEXT,
 algorithm_version VARCHAR(50) NOT NULL, created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_relationship_decisions_candidate_created
 ON relationship_decisions (candidate_id, created_at);

