CREATE TABLE benchmark_runs (
  id INTEGER PRIMARY KEY,
  engine_version VARCHAR(50) NOT NULL,
  metrics JSON NOT NULL,
  entity_count INTEGER NOT NULL,
  date_from TIMESTAMP WITH TIME ZONE,
  date_to TIMESTAMP WITH TIME ZONE,
  calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_benchmark_runs_calculated_id ON benchmark_runs (calculated_at, id);

CREATE TABLE benchmark_entries (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES benchmark_runs(id) ON DELETE CASCADE,
  entity_id VARCHAR(300) NOT NULL,
  observation_count INTEGER NOT NULL,
  metric_results JSON NOT NULL,
  overall_score FLOAT NOT NULL,
  overall_rank INTEGER NOT NULL,
  overall_percentile FLOAT NOT NULL
);
CREATE UNIQUE INDEX uq_benchmark_entries_run_entity
  ON benchmark_entries (run_id, entity_id);
CREATE INDEX ix_benchmark_entries_run_rank ON benchmark_entries (run_id, overall_rank);
CREATE INDEX ix_benchmark_entries_entity ON benchmark_entries (entity_id);

