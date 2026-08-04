CREATE TABLE insight_runs (
  id INTEGER PRIMARY KEY,
  engine_version VARCHAR(50) NOT NULL,
  request_payload JSON NOT NULL,
  source_record_count INTEGER NOT NULL,
  insight_count INTEGER NOT NULL,
  calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_insight_runs_calculated_id ON insight_runs (calculated_at, id);

CREATE TABLE insights (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES insight_runs(id) ON DELETE CASCADE,
  insight_type VARCHAR(30) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  entity_id VARCHAR(300),
  metric VARCHAR(50),
  title VARCHAR(300) NOT NULL,
  description TEXT NOT NULL,
  previous_value FLOAT,
  current_value FLOAT,
  absolute_change FLOAT,
  percentage_change FLOAT,
  confidence FLOAT NOT NULL,
  evidence JSON NOT NULL,
  recommendation TEXT
);
CREATE INDEX ix_insights_run_type ON insights (run_id, insight_type);
CREATE INDEX ix_insights_entity_metric ON insights (entity_id, metric);

