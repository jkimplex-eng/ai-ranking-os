CREATE TABLE recommendation_templates (
    id INTEGER PRIMARY KEY,
    template_code VARCHAR(100) NOT NULL,
    recommendation_type VARCHAR(100) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    steps JSON NOT NULL,
    expected_result TEXT NOT NULL,
    estimated_time VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_recommendation_templates_code_version
        UNIQUE (template_code, version)
);

CREATE INDEX ix_recommendation_templates_type_version
    ON recommendation_templates (recommendation_type, version);

ALTER TABLE recommendations ADD COLUMN template_id INTEGER;
ALTER TABLE recommendations
    ADD CONSTRAINT fk_recommendations_template_id
    FOREIGN KEY (template_id)
    REFERENCES recommendation_templates(id)
    ON DELETE SET NULL;

CREATE INDEX ix_recommendations_template_id
    ON recommendations (template_id);
