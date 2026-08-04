CREATE TABLE segment_definitions (
  id INTEGER PRIMARY KEY,
  code VARCHAR(100) NOT NULL,
  name VARCHAR(200) NOT NULL,
  segment_type VARCHAR(30) NOT NULL,
  rules JSON NOT NULL,
  version VARCHAR(50) NOT NULL,
  is_active BOOLEAN NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX uq_segment_definitions_code ON segment_definitions (code);
CREATE INDEX ix_segment_definitions_type_active ON segment_definitions (segment_type, is_active);

CREATE TABLE segment_evaluations (
  id INTEGER PRIMARY KEY,
  segment_id INTEGER NOT NULL REFERENCES segment_definitions(id) ON DELETE CASCADE,
  segment_version VARCHAR(50) NOT NULL,
  source_count INTEGER NOT NULL,
  matched_count INTEGER NOT NULL,
  evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_segment_evaluations_segment_time
  ON segment_evaluations (segment_id, evaluated_at);

CREATE TABLE segment_memberships (
  id INTEGER PRIMARY KEY,
  evaluation_id INTEGER NOT NULL REFERENCES segment_evaluations(id) ON DELETE CASCADE,
  member_key VARCHAR(64) NOT NULL,
  observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
  dimensions JSON NOT NULL,
  metrics JSON NOT NULL
);
CREATE UNIQUE INDEX uq_segment_memberships_evaluation_key
  ON segment_memberships (evaluation_id, member_key);
CREATE INDEX ix_segment_memberships_key ON segment_memberships (member_key);

