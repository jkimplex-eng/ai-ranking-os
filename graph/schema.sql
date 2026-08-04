CREATE TABLE graph_snapshots (
    id INTEGER PRIMARY KEY, structure_version VARCHAR(50) NOT NULL,
    node_count INTEGER NOT NULL, edge_count INTEGER NOT NULL,
    build_metadata JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_graph_snapshots_created ON graph_snapshots (created_at);
CREATE TABLE graph_nodes (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES graph_snapshots(id) ON DELETE CASCADE,
    external_id VARCHAR(300) NOT NULL, name VARCHAR(500) NOT NULL,
    canonical_name VARCHAR(500) NOT NULL, node_type VARCHAR(100) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL, aliases JSON NOT NULL, properties JSON NOT NULL
);
CREATE UNIQUE INDEX uq_graph_nodes_snapshot_external
    ON graph_nodes (snapshot_id, external_id);
CREATE INDEX ix_graph_nodes_snapshot_type ON graph_nodes (snapshot_id, node_type);
CREATE TABLE graph_edges (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES graph_snapshots(id) ON DELETE CASCADE,
    source_node_id INTEGER NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id INTEGER NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(100) NOT NULL, confidence DOUBLE PRECISION NOT NULL,
    properties JSON NOT NULL
);
CREATE INDEX ix_graph_edges_snapshot_type ON graph_edges (snapshot_id, edge_type);
CREATE UNIQUE INDEX uq_graph_edges_snapshot_nodes_type
    ON graph_edges (snapshot_id, source_node_id, target_node_id, edge_type);

