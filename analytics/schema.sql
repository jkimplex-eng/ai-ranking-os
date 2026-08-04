CREATE TABLE analytics_runs (
  id INTEGER PRIMARY KEY,
  engine_version VARCHAR(50) NOT NULL,
  query_payload JSON NOT NULL,
  result_payload JSON NOT NULL,
  source_record_count INTEGER NOT NULL,
  group_count INTEGER NOT NULL,
  calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_analytics_runs_calculated_id
  ON analytics_runs (calculated_at, id);
CREATE INDEX ix_analytics_runs_version_calculated
  ON analytics_runs (engine_version, calculated_at);

