CREATE TABLE recommendation_simulations (
    id INTEGER PRIMARY KEY,
    recommendation_id INTEGER NOT NULL
        REFERENCES recommendations(id) ON DELETE CASCADE,
    current_visibility DOUBLE PRECISION NOT NULL,
    predicted_visibility DOUBLE PRECISION NOT NULL,
    predicted_delta DOUBLE PRECISION NOT NULL,
    confidence_min DOUBLE PRECISION NOT NULL,
    confidence_expected DOUBLE PRECISION NOT NULL,
    confidence_max DOUBLE PRECISION NOT NULL,
    estimated_duration_days INTEGER NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_recommendation_simulations_current_visibility
        CHECK (current_visibility >= 0 AND current_visibility <= 100),
    CONSTRAINT ck_recommendation_simulations_predicted_visibility
        CHECK (predicted_visibility >= 0 AND predicted_visibility <= 100),
    CONSTRAINT ck_recommendation_simulations_confidence_order
        CHECK (confidence_min <= confidence_expected
            AND confidence_expected <= confidence_max),
    CONSTRAINT ck_recommendation_simulations_duration
        CHECK (estimated_duration_days > 0)
);

CREATE INDEX ix_recommendation_simulations_recommendation_created
    ON recommendation_simulations (recommendation_id, created_at);
