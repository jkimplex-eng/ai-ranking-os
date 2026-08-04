CREATE TABLE trend_series (
    id INTEGER PRIMARY KEY,
    entity_id UUID NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    moving_average_window INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_trend_series_entity_version UNIQUE (entity_id, model_version)
);

CREATE TABLE trend_snapshots (
    id INTEGER PRIMARY KEY,
    series_id INTEGER NOT NULL REFERENCES trend_series(id) ON DELETE CASCADE,
    source_count INTEGER NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_trend_snapshots_series_built
    ON trend_snapshots (series_id, built_at);

CREATE TABLE trend_points (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES trend_snapshots(id) ON DELETE CASCADE,
    research_id INTEGER NOT NULL,
    metric VARCHAR(30) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    moving_average DOUBLE PRECISION NOT NULL,
    percentage_change DOUBLE PRECISION,
    direction VARCHAR(10) NOT NULL
);

CREATE INDEX ix_trend_points_snapshot_metric_time
    ON trend_points (snapshot_id, metric, observed_at);

