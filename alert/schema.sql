CREATE TABLE alert_rules (
    id INTEGER PRIMARY KEY,
    code VARCHAR(100) NOT NULL,
    alert_type VARCHAR(60) NOT NULL,
    threshold DOUBLE PRECISION,
    severity VARCHAR(20) NOT NULL,
    version VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_alert_rules_code_version UNIQUE (code, version)
);

CREATE INDEX ix_alert_rules_active_version ON alert_rules (is_active, version);

CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    entity_id UUID NOT NULL,
    rule_id INTEGER NOT NULL REFERENCES alert_rules(id),
    alert_type VARCHAR(60) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    message TEXT NOT NULL,
    previous_value DOUBLE PRECISION,
    current_value DOUBLE PRECISION,
    context JSON NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_alerts_entity_detected ON alerts (entity_id, detected_at);
CREATE INDEX ix_alerts_rule_id ON alerts (rule_id);

CREATE TABLE alert_events (
    id INTEGER PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_alert_events_alert_created ON alert_events (alert_id, created_at);

