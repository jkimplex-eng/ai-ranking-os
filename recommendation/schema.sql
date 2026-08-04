CREATE TABLE recommendation_rules (
    id INTEGER PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    recommendation_type VARCHAR(100) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    operator VARCHAR(20) NOT NULL,
    threshold DOUBLE PRECISION NOT NULL,
    priority VARCHAR(20) NOT NULL,
    explanation_template TEXT NOT NULL,
    expected_effect TEXT NOT NULL,
    version VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_recommendation_rules_active_version
    ON recommendation_rules (is_active, version);

CREATE TABLE recommendation_executions (
    id INTEGER PRIMARY KEY,
    research_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    engine_version VARCHAR(50) NOT NULL,
    input_snapshot JSON NOT NULL,
    generated_count INTEGER NOT NULL,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_recommendation_executions_research_started
    ON recommendation_executions (research_id, started_at);

CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY,
    execution_id INTEGER NOT NULL
        REFERENCES recommendation_executions(id) ON DELETE CASCADE,
    rule_id INTEGER
        REFERENCES recommendation_rules(id) ON DELETE SET NULL,
    research_id INTEGER NOT NULL,
    recommendation_type VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    explanation TEXT NOT NULL,
    metric VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    expected_effect TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_recommendations_research_created
    ON recommendations (research_id, created_at);

CREATE INDEX ix_recommendations_execution_priority
    ON recommendations (execution_id, priority);

CREATE INDEX ix_recommendations_rule_id
    ON recommendations (rule_id);
