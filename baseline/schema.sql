CREATE TABLE baselines (
    id INTEGER PRIMARY KEY, entity_id UUID NOT NULL UNIQUE,
    research_id INTEGER NOT NULL, update_policy VARCHAR(30) NOT NULL,
    thresholds JSON NOT NULL, algorithm_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE baseline_snapshots (
    id INTEGER PRIMARY KEY,
    baseline_id INTEGER NOT NULL REFERENCES baselines(id) ON DELETE CASCADE,
    research_id INTEGER NOT NULL, visibility DOUBLE PRECISION NOT NULL,
    mention DOUBLE PRECISION NOT NULL, recommendation DOUBLE PRECISION NOT NULL,
    citation DOUBLE PRECISION NOT NULL, coverage DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL, reason VARCHAR(50) NOT NULL,
    algorithm_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_baseline_snapshots_baseline_created
    ON baseline_snapshots (baseline_id, created_at);
CREATE TABLE regression_events (
    id INTEGER PRIMARY KEY,
    baseline_id INTEGER NOT NULL REFERENCES baselines(id) ON DELETE CASCADE,
    baseline_snapshot_id INTEGER NOT NULL REFERENCES baseline_snapshots(id) ON DELETE CASCADE,
    current_research_id INTEGER NOT NULL, metric VARCHAR(30) NOT NULL,
    baseline_value DOUBLE PRECISION NOT NULL, current_value DOUBLE PRECISION NOT NULL,
    delta DOUBLE PRECISION NOT NULL, severity VARCHAR(20) NOT NULL,
    algorithm_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_regression_events_baseline_created
    ON regression_events (baseline_id, created_at);
CREATE INDEX ix_regression_events_snapshot_id
    ON regression_events (baseline_snapshot_id);

