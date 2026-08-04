CREATE TABLE researches (
    id INTEGER PRIMARY KEY,
    entity_id UUID,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    objective TEXT,
    status VARCHAR(20) NOT NULL,
    metadata_payload JSON NOT NULL,
    total_tasks INTEGER NOT NULL,
    completed_tasks INTEGER NOT NULL,
    failed_tasks INTEGER NOT NULL,
    progress_percent DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_researches_status_created_at
    ON researches (status, created_at);

CREATE INDEX ix_researches_entity_id
    ON researches (entity_id);

CREATE TABLE research_tasks (
    id INTEGER PRIMARY KEY,
    research_id INTEGER NOT NULL REFERENCES researches(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    priority INTEGER NOT NULL,
    provider VARCHAR(100),
    model VARCHAR(200),
    metadata_payload JSON NOT NULL,
    decision_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    execution_id INTEGER REFERENCES executions(id) ON DELETE SET NULL,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_research_tasks_research_id_status
    ON research_tasks (research_id, status);

CREATE TABLE research_responses (
    id INTEGER PRIMARY KEY,
    research_task_id INTEGER NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    raw_payload JSON NOT NULL,
    prompt TEXT NOT NULL,
    raw_response JSON NOT NULL,
    normalized_response JSON NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost DOUBLE PRECISION NOT NULL,
    latency_ms INTEGER,
    error_type VARCHAR(50),
    error_message TEXT,
    processing_status VARCHAR(20) NOT NULL,
    processing_error TEXT,
    finished_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_research_responses_task_created_at
    ON research_responses (research_task_id, created_at);

CREATE TABLE research_extracted_entities (
    id INTEGER PRIMARY KEY,
    response_id INTEGER NOT NULL REFERENCES research_responses(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    canonical_name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    aliases JSON NOT NULL,
    knowledge_graph_id VARCHAR(100),
    metadata_payload JSON NOT NULL
);

CREATE INDEX ix_research_entities_response_type
    ON research_extracted_entities (response_id, entity_type);

CREATE TABLE research_extracted_citations (
    id INTEGER PRIMARY KEY,
    response_id INTEGER NOT NULL REFERENCES research_responses(id) ON DELETE CASCADE,
    url TEXT,
    title VARCHAR(500),
    source VARCHAR(300),
    excerpt TEXT,
    position INTEGER NOT NULL,
    metadata_payload JSON NOT NULL
);

CREATE INDEX ix_research_citations_response
    ON research_extracted_citations (response_id);

CREATE TABLE research_extracted_recommendations (
    id INTEGER PRIMARY KEY,
    response_id INTEGER NOT NULL REFERENCES research_responses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    rank INTEGER NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    metadata_payload JSON NOT NULL
);

CREATE INDEX ix_research_recommendations_response
    ON research_extracted_recommendations (response_id);

CREATE TABLE research_scores (
    id INTEGER PRIMARY KEY,
    research_id INTEGER NOT NULL REFERENCES researches(id) ON DELETE CASCADE,
    mention_score DOUBLE PRECISION NOT NULL,
    recommendation_score DOUBLE PRECISION NOT NULL,
    citation_score DOUBLE PRECISION NOT NULL,
    coverage_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    visibility_score DOUBLE PRECISION NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    version VARCHAR(50) NOT NULL
);

CREATE UNIQUE INDEX uq_research_scores_research_version
    ON research_scores (research_id, version);

CREATE INDEX ix_research_scores_calculated_at
    ON research_scores (calculated_at);
