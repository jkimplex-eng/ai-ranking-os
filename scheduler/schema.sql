CREATE TABLE schedules (
    id INTEGER PRIMARY KEY, name VARCHAR(200) NOT NULL,
    research_id INTEGER NOT NULL, schedule_type VARCHAR(20) NOT NULL,
    cron_expression VARCHAR(100), models JSON NOT NULL, query TEXT,
    retry_policy JSON NOT NULL, is_enabled BOOLEAN NOT NULL,
    next_run_at TIMESTAMPTZ NOT NULL, last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_schedules_enabled_next_run ON schedules (is_enabled, next_run_at);

CREATE TABLE schedule_executions (
    id INTEGER PRIMARY KEY,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    research_id INTEGER, status VARCHAR(20) NOT NULL, attempts INTEGER NOT NULL,
    error TEXT, scheduled_for TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ NOT NULL, finished_at TIMESTAMPTZ
);
CREATE INDEX ix_schedule_executions_schedule_started
    ON schedule_executions (schedule_id, started_at);
CREATE UNIQUE INDEX uq_schedule_executions_one_running
    ON schedule_executions (schedule_id) WHERE status = 'RUNNING';

CREATE TABLE schedule_history (
    id INTEGER PRIMARY KEY,
    execution_id INTEGER NOT NULL REFERENCES schedule_executions(id) ON DELETE CASCADE,
    attempt INTEGER NOT NULL, status VARCHAR(20) NOT NULL, research_id INTEGER,
    error TEXT, retry_delay_seconds DOUBLE PRECISION NOT NULL,
    started_at TIMESTAMPTZ NOT NULL, finished_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_schedule_history_execution_attempt
    ON schedule_history (execution_id, attempt);

