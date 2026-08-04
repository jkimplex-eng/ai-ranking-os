CREATE TABLE influence_snapshots (
  id INTEGER PRIMARY KEY,
  graph_snapshot_id INTEGER NOT NULL,
  algorithm_version VARCHAR(50) NOT NULL,
  node_count INTEGER NOT NULL,
  edge_count INTEGER NOT NULL,
  calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_influence_snapshot_graph_version
    UNIQUE (graph_snapshot_id, algorithm_version)
);

CREATE INDEX ix_influence_snapshots_calculated
  ON influence_snapshots (calculated_at);

CREATE TABLE entity_influence (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES influence_snapshots(id) ON DELETE CASCADE,
  entity_id VARCHAR(300) NOT NULL,
  name VARCHAR(500) NOT NULL,
  node_type VARCHAR(100) NOT NULL,
  degree FLOAT NOT NULL,
  weighted_degree FLOAT NOT NULL,
  pagerank FLOAT NOT NULL,
  betweenness FLOAT NOT NULL,
  closeness FLOAT NOT NULL,
  influence_score FLOAT NOT NULL,
  rank INTEGER NOT NULL,
  CONSTRAINT uq_entity_influence_snapshot_entity UNIQUE (snapshot_id, entity_id)
);

CREATE INDEX ix_entity_influence_entity ON entity_influence (entity_id);
CREATE INDEX ix_entity_influence_snapshot_rank ON entity_influence (snapshot_id, rank);

