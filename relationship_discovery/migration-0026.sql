BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE system_events (
    id SERIAL NOT NULL, 
    event_type VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_system_events_event_type ON system_events (event_type);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE TABLE projects (
    id SERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE agents (
    id SERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE sprints (
    id SERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    goal TEXT, 
    starts_on DATE, 
    ends_on DATE, 
    project_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
);

CREATE TABLE tasks (
    id SERIAL NOT NULL, 
    title VARCHAR(300) NOT NULL, 
    description TEXT, 
    status VARCHAR(20) NOT NULL, 
    owner_id INTEGER, 
    sprint_id INTEGER, 
    project_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES agents (id) ON DELETE SET NULL, 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL, 
    FOREIGN KEY(sprint_id) REFERENCES sprints (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_tasks_owner_in_progress ON tasks (owner_id) WHERE status = 'IN_PROGRESS' AND owner_id IS NOT NULL;

CREATE TABLE execution_logs (
    id SERIAL NOT NULL, 
    entity_type VARCHAR(50) NOT NULL, 
    entity_id INTEGER NOT NULL, 
    action VARCHAR(50) NOT NULL, 
    changes JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_execution_logs_entity_id ON execution_logs (entity_id);

CREATE INDEX ix_execution_logs_entity_type ON execution_logs (entity_type);

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

-- Running upgrade 0002 -> 0003

ALTER TABLE agents ADD COLUMN agent_type VARCHAR(20) DEFAULT 'CODEX' NOT NULL;

ALTER TABLE agents ADD COLUMN specialization VARCHAR(100);

ALTER TABLE agents ADD COLUMN is_enabled BOOLEAN DEFAULT true NOT NULL;

CREATE INDEX ix_agents_specialization ON agents (specialization);

ALTER TABLE tasks ADD COLUMN priority VARCHAR(10) DEFAULT 'MEDIUM' NOT NULL;

ALTER TABLE tasks ADD COLUMN required_specialization VARCHAR(100);

CREATE INDEX ix_tasks_required_specialization ON tasks (required_specialization);

CREATE TABLE executions (
    id SERIAL NOT NULL, 
    task_id INTEGER NOT NULL, 
    agent_id INTEGER, 
    state VARCHAR(20) DEFAULT 'PENDING' NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    duration_ms INTEGER, 
    result JSON, 
    error TEXT, 
    attempt_count INTEGER DEFAULT '0' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(agent_id) REFERENCES agents (id), 
    FOREIGN KEY(task_id) REFERENCES tasks (id)
);

CREATE INDEX ix_executions_agent_id ON executions (agent_id);

CREATE INDEX ix_executions_state ON executions (state);

CREATE INDEX ix_executions_task_id ON executions (task_id);

CREATE UNIQUE INDEX uq_executions_active_task ON executions (task_id) WHERE state IN ('PENDING', 'ASSIGNED', 'RUNNING', 'WAITING_REVIEW');

CREATE UNIQUE INDEX uq_executions_active_agent ON executions (agent_id) WHERE state IN ('ASSIGNED', 'RUNNING', 'WAITING_REVIEW') AND agent_id IS NOT NULL;

UPDATE alembic_version SET version_num='0003' WHERE alembic_version.version_num = '0002';

-- Running upgrade 0003 -> 0004

CREATE TABLE visibility_weight_sets (
    id SERIAL NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    weights JSON NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (version)
);

CREATE INDEX ix_visibility_weight_sets_is_active ON visibility_weight_sets (is_active);

INSERT INTO visibility_weight_sets (version, weights, is_active) VALUES ('1.0', '{"mention_frequency":0.2,"recommendation_position":0.15,"citation_count":0.1,"citation_authority":0.15,"cross_model_presence":0.15,"consistency":0.1,"entity_confidence":0.1,"freshness":0.05}', true);

CREATE TABLE visibility_calculations (
    id SERIAL NOT NULL, 
    entity_id VARCHAR(200) NOT NULL, 
    entity VARCHAR(300) NOT NULL, 
    visibility_score FLOAT NOT NULL, 
    confidence FLOAT NOT NULL, 
    metrics JSON NOT NULL, 
    weights JSON NOT NULL, 
    weight_version VARCHAR(50) NOT NULL, 
    input_payload JSON NOT NULL, 
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_visibility_calculations_calculated_at ON visibility_calculations (calculated_at);

CREATE INDEX ix_visibility_calculations_entity_id ON visibility_calculations (entity_id);

CREATE INDEX ix_visibility_calculations_weight_version ON visibility_calculations (weight_version);

UPDATE alembic_version SET version_num='0004' WHERE alembic_version.version_num = '0003';

-- Running upgrade 0004 -> 0005

CREATE TABLE entity_extraction_runs (
    id SERIAL NOT NULL, 
    response_id VARCHAR(200) NOT NULL, 
    model VARCHAR(100), 
    raw_response JSON NOT NULL, 
    output_payload JSON NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (response_id)
);

CREATE INDEX ix_entity_extraction_runs_processed_at ON entity_extraction_runs (processed_at);

CREATE UNIQUE INDEX ix_entity_extraction_runs_response_id ON entity_extraction_runs (response_id);

CREATE TABLE entity_history (
    id SERIAL NOT NULL, 
    run_id INTEGER NOT NULL, 
    response_id VARCHAR(200) NOT NULL, 
    entity_id VARCHAR(100) NOT NULL, 
    name VARCHAR(500) NOT NULL, 
    canonical_name VARCHAR(500) NOT NULL, 
    entity_type VARCHAR(50) NOT NULL, 
    confidence FLOAT NOT NULL, 
    aliases JSON NOT NULL, 
    knowledge_graph_id VARCHAR(100) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES entity_extraction_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_entity_history_canonical_name ON entity_history (canonical_name);

CREATE INDEX ix_entity_history_entity_type ON entity_history (entity_type);

CREATE INDEX ix_entity_history_knowledge_graph_id ON entity_history (knowledge_graph_id);

CREATE INDEX ix_entity_history_response_id ON entity_history (response_id);

CREATE TABLE relation_history (
    id SERIAL NOT NULL, 
    run_id INTEGER NOT NULL, 
    response_id VARCHAR(200) NOT NULL, 
    relation_id VARCHAR(100) NOT NULL, 
    source_entity_id VARCHAR(100) NOT NULL, 
    target_entity_id VARCHAR(100) NOT NULL, 
    relation_type VARCHAR(50) NOT NULL, 
    confidence FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES entity_extraction_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_relation_history_relation_type ON relation_history (relation_type);

CREATE INDEX ix_relation_history_response_id ON relation_history (response_id);

CREATE TABLE resolution_log_history (
    id SERIAL NOT NULL, 
    run_id INTEGER NOT NULL, 
    response_id VARCHAR(200) NOT NULL, 
    stage VARCHAR(100) NOT NULL, 
    action VARCHAR(100) NOT NULL, 
    details JSON NOT NULL, 
    message TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES entity_extraction_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_resolution_log_history_response_id ON resolution_log_history (response_id);

CREATE INDEX ix_resolution_log_history_stage ON resolution_log_history (stage);

UPDATE alembic_version SET version_num='0005' WHERE alembic_version.version_num = '0004';

-- Running upgrade 0005 -> 0006

CREATE TABLE intent_classification_runs (
    id SERIAL NOT NULL, 
    request_id VARCHAR(200) NOT NULL, 
    query TEXT NOT NULL, 
    language VARCHAR(20) NOT NULL, 
    primary_intent VARCHAR(50) NOT NULL, 
    confidence FLOAT NOT NULL, 
    output_payload JSON NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    classified_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (request_id)
);

CREATE INDEX ix_intent_classification_runs_classified_at ON intent_classification_runs (classified_at);

CREATE INDEX ix_intent_classification_runs_language ON intent_classification_runs (language);

CREATE INDEX ix_intent_classification_runs_primary_intent ON intent_classification_runs (primary_intent);

CREATE UNIQUE INDEX ix_intent_classification_runs_request_id ON intent_classification_runs (request_id);

CREATE TABLE intent_history (
    id SERIAL NOT NULL, 
    run_id INTEGER NOT NULL, 
    request_id VARCHAR(200) NOT NULL, 
    intent VARCHAR(50) NOT NULL, 
    subtype VARCHAR(100) NOT NULL, 
    confidence FLOAT NOT NULL, 
    is_primary BOOLEAN NOT NULL, 
    signals JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES intent_classification_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_intent_history_intent ON intent_history (intent);

CREATE INDEX ix_intent_history_request_id ON intent_history (request_id);

CREATE TABLE confidence_history (
    id SERIAL NOT NULL, 
    run_id INTEGER NOT NULL, 
    request_id VARCHAR(200) NOT NULL, 
    source VARCHAR(50) NOT NULL, 
    intent VARCHAR(50) NOT NULL, 
    confidence FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES intent_classification_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_confidence_history_intent ON confidence_history (intent);

CREATE INDEX ix_confidence_history_request_id ON confidence_history (request_id);

CREATE INDEX ix_confidence_history_source ON confidence_history (source);

CREATE TABLE routing_metadata (
    id SERIAL NOT NULL, 
    run_id INTEGER NOT NULL, 
    request_id VARCHAR(200) NOT NULL, 
    strategy VARCHAR(100) NOT NULL, 
    llm_fallback_required BOOLEAN NOT NULL, 
    metadata_payload JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES intent_classification_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_routing_metadata_request_id ON routing_metadata (request_id);

CREATE INDEX ix_routing_metadata_strategy ON routing_metadata (strategy);

UPDATE alembic_version SET version_num='0006' WHERE alembic_version.version_num = '0005';

-- Running upgrade 0006 -> 0007

CREATE TABLE query_execution_history (
    id SERIAL NOT NULL, 
    execution_id VARCHAR(200) NOT NULL, 
    plan_id VARCHAR(200) NOT NULL, 
    request_id VARCHAR(200), 
    mode VARCHAR(30) NOT NULL, 
    state VARCHAR(30) NOT NULL, 
    plan_payload JSON NOT NULL, 
    output_payload JSON, 
    error TEXT, 
    started_at TIMESTAMP WITH TIME ZONE, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    duration_ms INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (execution_id)
);

CREATE UNIQUE INDEX ix_query_execution_history_execution_id ON query_execution_history (execution_id);

CREATE INDEX ix_query_execution_history_mode ON query_execution_history (mode);

CREATE INDEX ix_query_execution_history_plan_id ON query_execution_history (plan_id);

CREATE INDEX ix_query_execution_history_request_id ON query_execution_history (request_id);

CREATE INDEX ix_query_execution_history_state ON query_execution_history (state);

CREATE TABLE query_execution_metrics (
    id SERIAL NOT NULL, 
    execution_row_id INTEGER NOT NULL, 
    execution_id VARCHAR(200) NOT NULL, 
    metric_name VARCHAR(100) NOT NULL, 
    metric_value FLOAT NOT NULL, 
    unit VARCHAR(30) NOT NULL, 
    metadata_payload JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(execution_row_id) REFERENCES query_execution_history (id) ON DELETE CASCADE
);

CREATE INDEX ix_query_execution_metrics_execution_id ON query_execution_metrics (execution_id);

CREATE INDEX ix_query_execution_metrics_metric_name ON query_execution_metrics (metric_name);

CREATE TABLE query_provider_metrics (
    id SERIAL NOT NULL, 
    execution_row_id INTEGER NOT NULL, 
    execution_id VARCHAR(200) NOT NULL, 
    step_id VARCHAR(200) NOT NULL, 
    provider VARCHAR(100) NOT NULL, 
    state VARCHAR(30) NOT NULL, 
    attempts INTEGER NOT NULL, 
    latency_ms INTEGER NOT NULL, 
    failure TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(execution_row_id) REFERENCES query_execution_history (id) ON DELETE CASCADE
);

CREATE INDEX ix_query_provider_metrics_execution_id ON query_provider_metrics (execution_id);

CREATE INDEX ix_query_provider_metrics_provider ON query_provider_metrics (provider);

CREATE INDEX ix_query_provider_metrics_state ON query_provider_metrics (state);

UPDATE alembic_version SET version_num='0007' WHERE alembic_version.version_num = '0006';

-- Running upgrade 0007 -> 0008

CREATE TABLE router_models (
    id VARCHAR(200) NOT NULL, 
    provider VARCHAR(100) NOT NULL, 
    display_name VARCHAR(300) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    tier VARCHAR(30) NOT NULL, 
    capabilities JSON NOT NULL, 
    input_cost_per_million FLOAT NOT NULL, 
    output_cost_per_million FLOAT NOT NULL, 
    latency_ms FLOAT NOT NULL, 
    quality FLOAT NOT NULL, 
    availability FLOAT NOT NULL, 
    context_window INTEGER NOT NULL, 
    hallucination_rate FLOAT NOT NULL, 
    domains JSON NOT NULL, 
    languages JSON NOT NULL, 
    metadata_payload JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_router_models_provider ON router_models (provider);

CREATE INDEX ix_router_models_status ON router_models (status);

CREATE INDEX ix_router_models_tier ON router_models (tier);

CREATE TABLE router_policies (
    id VARCHAR(100) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    enabled BOOLEAN NOT NULL, 
    execution_mode VARCHAR(30) NOT NULL, 
    top_k INTEGER NOT NULL, 
    weights JSON NOT NULL, 
    required_capabilities JSON NOT NULL, 
    daily_budget_usd FLOAT, 
    monthly_budget_usd FLOAT, 
    settings JSON NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_router_policies_enabled ON router_policies (enabled);

CREATE TABLE router_history (
    id SERIAL NOT NULL, 
    correlation_id VARCHAR(200) NOT NULL, 
    query TEXT NOT NULL, 
    intent VARCHAR(50) NOT NULL, 
    policy_id VARCHAR(100) NOT NULL, 
    selected_models JSON NOT NULL, 
    execution_mode VARCHAR(30) NOT NULL, 
    routing_scores JSON NOT NULL, 
    estimated_cost_usd FLOAT NOT NULL, 
    latency_ms FLOAT NOT NULL, 
    fallback_count INTEGER NOT NULL, 
    budget_downgraded BOOLEAN NOT NULL, 
    error TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_router_history_correlation_id ON router_history (correlation_id);

CREATE INDEX ix_router_history_intent ON router_history (intent);

CREATE INDEX ix_router_history_policy_id ON router_history (policy_id);

CREATE INDEX ix_router_history_created_at ON router_history (created_at);

CREATE TABLE router_cost_logs (
    id SERIAL NOT NULL, 
    correlation_id VARCHAR(200) NOT NULL, 
    model_id VARCHAR(200) NOT NULL, 
    provider VARCHAR(100) NOT NULL, 
    input_tokens INTEGER NOT NULL, 
    output_tokens INTEGER NOT NULL, 
    cost_usd FLOAT NOT NULL, 
    cost_type VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_router_cost_logs_correlation_id ON router_cost_logs (correlation_id);

CREATE INDEX ix_router_cost_logs_model_id ON router_cost_logs (model_id);

CREATE INDEX ix_router_cost_logs_provider ON router_cost_logs (provider);

CREATE INDEX ix_router_cost_logs_created_at ON router_cost_logs (created_at);

CREATE TABLE router_circuit_breakers (
    model_id VARCHAR(200) NOT NULL, 
    state VARCHAR(30) NOT NULL, 
    failure_count INTEGER NOT NULL, 
    success_count INTEGER NOT NULL, 
    opened_at TIMESTAMP WITH TIME ZONE, 
    last_failure_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (model_id)
);

CREATE INDEX ix_router_circuit_breakers_state ON router_circuit_breakers (state);

UPDATE alembic_version SET version_num='0008' WHERE alembic_version.version_num = '0007';

-- Running upgrade 0008 -> 0009

ALTER TABLE router_models ADD COLUMN region VARCHAR(20) DEFAULT 'GLOBAL' NOT NULL;

ALTER TABLE router_models ADD COLUMN success_probability FLOAT DEFAULT '0.95' NOT NULL;

CREATE INDEX ix_router_models_region ON router_models (region);

UPDATE alembic_version SET version_num='0009' WHERE alembic_version.version_num = '0008';

-- Running upgrade 0009 -> 0010

CREATE TABLE provider_usage (
    id SERIAL NOT NULL, 
    execution_id VARCHAR(200) NOT NULL, 
    provider VARCHAR(100) NOT NULL, 
    model VARCHAR(200) NOT NULL, 
    prompt_tokens INTEGER NOT NULL, 
    completion_tokens INTEGER NOT NULL, 
    total_tokens INTEGER NOT NULL, 
    estimated_cost FLOAT NOT NULL, 
    currency VARCHAR(10) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_provider_usage_execution_id ON provider_usage (execution_id);

CREATE INDEX ix_provider_usage_provider ON provider_usage (provider);

CREATE INDEX ix_provider_usage_model ON provider_usage (model);

CREATE INDEX ix_provider_usage_created_at ON provider_usage (created_at);

UPDATE alembic_version SET version_num='0010' WHERE alembic_version.version_num = '0009';

-- Running upgrade 0010 -> 0011

CREATE TABLE researches (
    id SERIAL NOT NULL, 
    title VARCHAR(300) NOT NULL, 
    description TEXT, 
    objective TEXT, 
    status VARCHAR(20) NOT NULL, 
    metadata_payload JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_researches_status_created_at ON researches (status, created_at);

CREATE TABLE research_tasks (
    id SERIAL NOT NULL, 
    research_id INTEGER NOT NULL, 
    query TEXT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    priority INTEGER NOT NULL, 
    provider VARCHAR(100), 
    model VARCHAR(200), 
    metadata_payload JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(research_id) REFERENCES researches (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_tasks_research_id_status ON research_tasks (research_id, status);

CREATE TABLE research_responses (
    id SERIAL NOT NULL, 
    research_task_id INTEGER NOT NULL, 
    provider VARCHAR(100) NOT NULL, 
    model VARCHAR(200) NOT NULL, 
    content TEXT NOT NULL, 
    raw_payload JSON NOT NULL, 
    prompt_tokens INTEGER NOT NULL, 
    completion_tokens INTEGER NOT NULL, 
    total_tokens INTEGER NOT NULL, 
    latency_ms INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(research_task_id) REFERENCES research_tasks (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_responses_task_created_at ON research_responses (research_task_id, created_at);

UPDATE alembic_version SET version_num='0011' WHERE alembic_version.version_num = '0010';

-- Running upgrade 0011 -> 0012

ALTER TABLE researches ADD COLUMN total_tasks INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE researches ADD COLUMN completed_tasks INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE researches ADD COLUMN failed_tasks INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE researches ADD COLUMN progress_percent FLOAT DEFAULT '0' NOT NULL;

ALTER TABLE research_tasks ADD COLUMN decision_task_id INTEGER;

ALTER TABLE research_tasks ADD COLUMN execution_id INTEGER;

ALTER TABLE research_tasks ADD COLUMN error TEXT;

ALTER TABLE research_tasks ADD CONSTRAINT fk_research_tasks_decision_task_id FOREIGN KEY(decision_task_id) REFERENCES tasks (id) ON DELETE SET NULL;

ALTER TABLE research_tasks ADD CONSTRAINT fk_research_tasks_execution_id FOREIGN KEY(execution_id) REFERENCES executions (id) ON DELETE SET NULL;

CREATE INDEX ix_research_tasks_decision_task_id ON research_tasks (decision_task_id);

CREATE INDEX ix_research_tasks_execution_id ON research_tasks (execution_id);

UPDATE alembic_version SET version_num='0012' WHERE alembic_version.version_num = '0011';

-- Running upgrade 0012 -> 0013

ALTER TABLE research_responses ADD COLUMN prompt TEXT DEFAULT '' NOT NULL;

ALTER TABLE research_responses ADD COLUMN raw_response JSON DEFAULT '{}' NOT NULL;

ALTER TABLE research_responses ADD COLUMN normalized_response JSON DEFAULT '{}' NOT NULL;

ALTER TABLE research_responses ADD COLUMN input_tokens INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE research_responses ADD COLUMN output_tokens INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE research_responses ADD COLUMN cost FLOAT DEFAULT '0' NOT NULL;

ALTER TABLE research_responses ADD COLUMN error_type VARCHAR(50);

ALTER TABLE research_responses ADD COLUMN error_message TEXT;

ALTER TABLE research_responses ADD COLUMN finished_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL;

UPDATE research_responses SET raw_response = raw_payload, input_tokens = prompt_tokens, output_tokens = completion_tokens, finished_at = created_at;

UPDATE alembic_version SET version_num='0013' WHERE alembic_version.version_num = '0012';

-- Running upgrade 0013 -> 0014

ALTER TABLE research_responses ADD COLUMN processing_status VARCHAR(20) DEFAULT 'NORMALIZED' NOT NULL;

ALTER TABLE research_responses ADD COLUMN processing_error TEXT;

CREATE TABLE research_extracted_entities (
    id SERIAL NOT NULL, 
    response_id INTEGER NOT NULL, 
    name VARCHAR(500) NOT NULL, 
    canonical_name VARCHAR(500) NOT NULL, 
    entity_type VARCHAR(50) NOT NULL, 
    confidence FLOAT NOT NULL, 
    aliases JSON NOT NULL, 
    knowledge_graph_id VARCHAR(100), 
    metadata_payload JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(response_id) REFERENCES research_responses (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_entities_response_type ON research_extracted_entities (response_id, entity_type);

CREATE TABLE research_extracted_citations (
    id SERIAL NOT NULL, 
    response_id INTEGER NOT NULL, 
    url TEXT, 
    title VARCHAR(500), 
    source VARCHAR(300), 
    excerpt TEXT, 
    position INTEGER NOT NULL, 
    metadata_payload JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(response_id) REFERENCES research_responses (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_citations_response ON research_extracted_citations (response_id);

CREATE TABLE research_extracted_recommendations (
    id SERIAL NOT NULL, 
    response_id INTEGER NOT NULL, 
    content TEXT NOT NULL, 
    rank INTEGER NOT NULL, 
    confidence FLOAT NOT NULL, 
    metadata_payload JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(response_id) REFERENCES research_responses (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_recommendations_response ON research_extracted_recommendations (response_id);

UPDATE alembic_version SET version_num='0014' WHERE alembic_version.version_num = '0013';

-- Running upgrade 0014 -> 0015

CREATE TABLE research_scores (
    id SERIAL NOT NULL, 
    research_id INTEGER NOT NULL, 
    mention_score FLOAT NOT NULL, 
    recommendation_score FLOAT NOT NULL, 
    citation_score FLOAT NOT NULL, 
    coverage_score FLOAT NOT NULL, 
    confidence_score FLOAT NOT NULL, 
    visibility_score FLOAT NOT NULL, 
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(research_id) REFERENCES researches (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_research_scores_research_version ON research_scores (research_id, version);

CREATE INDEX ix_research_scores_calculated_at ON research_scores (calculated_at);

UPDATE alembic_version SET version_num='0015' WHERE alembic_version.version_num = '0014';

-- Running upgrade 0015 -> 0016

ALTER TABLE researches ADD COLUMN entity_id UUID;

CREATE INDEX ix_researches_entity_id ON researches (entity_id);

UPDATE alembic_version SET version_num='0016' WHERE alembic_version.version_num = '0015';

-- Running upgrade 0016 -> 0017

CREATE TABLE recommendation_rules (
    id SERIAL NOT NULL, 
    code VARCHAR(100) NOT NULL, 
    recommendation_type VARCHAR(100) NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    operator VARCHAR(20) NOT NULL, 
    threshold FLOAT NOT NULL, 
    priority VARCHAR(20) NOT NULL, 
    explanation_template TEXT NOT NULL, 
    expected_effect TEXT NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE INDEX ix_recommendation_rules_active_version ON recommendation_rules (is_active, version);

CREATE TABLE recommendation_executions (
    id SERIAL NOT NULL, 
    research_id INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    engine_version VARCHAR(50) NOT NULL, 
    input_snapshot JSON NOT NULL, 
    generated_count INTEGER NOT NULL, 
    error TEXT, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_recommendation_executions_research_started ON recommendation_executions (research_id, started_at);

CREATE TABLE recommendations (
    id SERIAL NOT NULL, 
    execution_id INTEGER NOT NULL, 
    rule_id INTEGER, 
    research_id INTEGER NOT NULL, 
    recommendation_type VARCHAR(100) NOT NULL, 
    priority VARCHAR(20) NOT NULL, 
    explanation TEXT NOT NULL, 
    metric VARCHAR(100) NOT NULL, 
    metric_value FLOAT NOT NULL, 
    expected_effect TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(execution_id) REFERENCES recommendation_executions (id) ON DELETE CASCADE, 
    FOREIGN KEY(rule_id) REFERENCES recommendation_rules (id) ON DELETE SET NULL
);

CREATE INDEX ix_recommendations_research_created ON recommendations (research_id, created_at);

CREATE INDEX ix_recommendations_execution_priority ON recommendations (execution_id, priority);

CREATE INDEX ix_recommendations_rule_id ON recommendations (rule_id);

INSERT INTO recommendation_rules (code, recommendation_type, metric, operator, threshold, priority, explanation_template, expected_effect, version, is_active) VALUES ('v1-low-mention', 'MENTION_GROWTH', 'mention_score', 'lt', 60.0, 'HIGH', 'Mention Score {metric_value} is below {threshold}. Increase the number of relevant, high-quality mentions.', 'Raise Mention Score to at least 60.', '1.0', true);

INSERT INTO recommendation_rules (code, recommendation_type, metric, operator, threshold, priority, explanation_template, expected_effect, version, is_active) VALUES ('v1-low-citation', 'CITATION_AUTHORITY', 'citation_score', 'lt', 50.0, 'HIGH', 'Citation Score {metric_value} is below {threshold}. Add more authoritative and independently verifiable sources.', 'Raise Citation Score to at least 50.', '1.0', true);

INSERT INTO recommendation_rules (code, recommendation_type, metric, operator, threshold, priority, explanation_template, expected_effect, version, is_active) VALUES ('v1-low-recommendation', 'TRUST_SIGNALS', 'recommendation_score', 'lt', 60.0, 'CRITICAL', 'Recommendation Score {metric_value} is below {threshold}. Strengthen evidence, reviews, and trust signals.', 'Raise Recommendation Score to at least 60.', '1.0', true);

INSERT INTO recommendation_rules (code, recommendation_type, metric, operator, threshold, priority, explanation_template, expected_effect, version, is_active) VALUES ('v1-low-coverage', 'SOURCE_EXPANSION', 'coverage_score', 'lt', 70.0, 'MEDIUM', 'Coverage Score {metric_value} is below {threshold}. Expand presence across additional models and sources.', 'Raise Coverage Score to at least 70.', '1.0', true);

UPDATE alembic_version SET version_num='0017' WHERE alembic_version.version_num = '0016';

-- Running upgrade 0017 -> 0018

CREATE TABLE recommendation_templates (
    id SERIAL NOT NULL, 
    template_code VARCHAR(100) NOT NULL, 
    recommendation_type VARCHAR(100) NOT NULL, 
    title VARCHAR(300) NOT NULL, 
    description TEXT NOT NULL, 
    steps JSON NOT NULL, 
    expected_result TEXT NOT NULL, 
    estimated_time VARCHAR(100) NOT NULL, 
    priority VARCHAR(20) NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_recommendation_templates_code_version UNIQUE (template_code, version)
);

CREATE INDEX ix_recommendation_templates_type_version ON recommendation_templates (recommendation_type, version);

ALTER TABLE recommendations ADD COLUMN template_id INTEGER;

ALTER TABLE recommendations ADD CONSTRAINT fk_recommendations_template_id FOREIGN KEY(template_id) REFERENCES recommendation_templates (id) ON DELETE SET NULL;

CREATE INDEX ix_recommendations_template_id ON recommendations (template_id);

INSERT INTO recommendation_templates (template_code, recommendation_type, title, description, steps, expected_result, estimated_time, priority, version) VALUES ('mention-quality-plan', 'MENTION_GROWTH', 'Increase high-quality entity mentions', 'Build consistent, attributable mentions in relevant sources.', CAST('["Audit current mentions and identify missing authoritative sources.", "Prepare consistent entity descriptions and factual proof points.", "Publish or update content in the highest-priority sources.", "Repeat the research and compare Mention Score."]' AS JSON), 'More frequent and consistent entity mentions.', '2-4 weeks', 'HIGH', '1.0') RETURNING recommendation_templates.id;

INSERT INTO recommendation_templates (template_code, recommendation_type, title, description, steps, expected_result, estimated_time, priority, version) VALUES ('citation-authority-plan', 'CITATION_AUTHORITY', 'Strengthen authoritative citations', 'Increase independently verifiable, trusted references.', CAST('["Map existing citations and authority gaps.", "Create evidence assets with stable URLs and clear authorship.", "Secure references from reputable independent publications.", "Validate citation discovery in a follow-up research run."]' AS JSON), 'Higher citation frequency and source authority.', '3-6 weeks', 'HIGH', '1.0') RETURNING recommendation_templates.id;

INSERT INTO recommendation_templates (template_code, recommendation_type, title, description, steps, expected_result, estimated_time, priority, version) VALUES ('trust-signals-plan', 'TRUST_SIGNALS', 'Improve recommendation trust signals', 'Make quality, proof, and third-party validation explicit.', CAST('["Inventory reviews, certifications, case studies, and guarantees.", "Resolve inconsistent claims across owned properties.", "Publish evidence-backed comparisons and customer outcomes.", "Measure Recommendation Score after signals are indexed."]' AS JSON), 'Stronger evidence supporting model recommendations.', '2-5 weeks', 'CRITICAL', '1.0') RETURNING recommendation_templates.id;

INSERT INTO recommendation_templates (template_code, recommendation_type, title, description, steps, expected_result, estimated_time, priority, version) VALUES ('source-expansion-plan', 'SOURCE_EXPANSION', 'Expand model and source coverage', 'Increase presence across sources used by additional models.', CAST('["Identify models and source categories with no current presence.", "Prioritize sources shared by multiple target models.", "Publish localized or domain-specific entity content.", "Run a cross-model research comparison."]' AS JSON), 'Broader cross-model and cross-source coverage.', '3-8 weeks', 'MEDIUM', '1.0') RETURNING recommendation_templates.id;

UPDATE alembic_version SET version_num='0018' WHERE alembic_version.version_num = '0017';

-- Running upgrade 0018 -> 0019

CREATE TABLE recommendation_simulations (
    id SERIAL NOT NULL, 
    recommendation_id INTEGER NOT NULL, 
    current_visibility FLOAT NOT NULL, 
    predicted_visibility FLOAT NOT NULL, 
    predicted_delta FLOAT NOT NULL, 
    confidence_min FLOAT NOT NULL, 
    confidence_expected FLOAT NOT NULL, 
    confidence_max FLOAT NOT NULL, 
    estimated_duration_days INTEGER NOT NULL, 
    model_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_recommendation_simulations_current_visibility CHECK (current_visibility >= 0 AND current_visibility <= 100), 
    CONSTRAINT ck_recommendation_simulations_predicted_visibility CHECK (predicted_visibility >= 0 AND predicted_visibility <= 100), 
    CONSTRAINT ck_recommendation_simulations_confidence_order CHECK (confidence_min <= confidence_expected AND confidence_expected <= confidence_max), 
    CONSTRAINT ck_recommendation_simulations_duration CHECK (estimated_duration_days > 0), 
    FOREIGN KEY(recommendation_id) REFERENCES recommendations (id) ON DELETE CASCADE
);

CREATE INDEX ix_recommendation_simulations_recommendation_created ON recommendation_simulations (recommendation_id, created_at);

UPDATE alembic_version SET version_num='0019' WHERE alembic_version.version_num = '0018';

-- Running upgrade 0019 -> 0020

CREATE TABLE trend_series (
    id SERIAL NOT NULL, 
    entity_id UUID NOT NULL, 
    model_version VARCHAR(50) NOT NULL, 
    moving_average_window INTEGER DEFAULT '3' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_trend_series_entity_version ON trend_series (entity_id, model_version);

CREATE TABLE trend_snapshots (
    id SERIAL NOT NULL, 
    series_id INTEGER NOT NULL, 
    source_count INTEGER NOT NULL, 
    built_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(series_id) REFERENCES trend_series (id) ON DELETE CASCADE
);

CREATE INDEX ix_trend_snapshots_series_built ON trend_snapshots (series_id, built_at);

CREATE TABLE trend_points (
    id SERIAL NOT NULL, 
    snapshot_id INTEGER NOT NULL, 
    research_id INTEGER NOT NULL, 
    metric VARCHAR(30) NOT NULL, 
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    value FLOAT NOT NULL, 
    moving_average FLOAT NOT NULL, 
    percentage_change FLOAT, 
    direction VARCHAR(10) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(snapshot_id) REFERENCES trend_snapshots (id) ON DELETE CASCADE
);

CREATE INDEX ix_trend_points_snapshot_metric_time ON trend_points (snapshot_id, metric, observed_at);

UPDATE alembic_version SET version_num='0020' WHERE alembic_version.version_num = '0019';

-- Running upgrade 0020 -> 0021

CREATE TABLE alert_rules (
    id SERIAL NOT NULL, 
    code VARCHAR(100) NOT NULL, 
    alert_type VARCHAR(60) NOT NULL, 
    threshold FLOAT, 
    severity VARCHAR(20) NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_alert_rules_code_version ON alert_rules (code, version);

CREATE INDEX ix_alert_rules_active_version ON alert_rules (is_active, version);

CREATE TABLE alerts (
    id SERIAL NOT NULL, 
    entity_id UUID NOT NULL, 
    rule_id INTEGER NOT NULL, 
    alert_type VARCHAR(60) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    title VARCHAR(300) NOT NULL, 
    message TEXT NOT NULL, 
    previous_value FLOAT, 
    current_value FLOAT, 
    context JSON NOT NULL, 
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(rule_id) REFERENCES alert_rules (id)
);

CREATE INDEX ix_alerts_entity_detected ON alerts (entity_id, detected_at);

CREATE INDEX ix_alerts_rule_id ON alerts (rule_id);

CREATE TABLE alert_events (
    id SERIAL NOT NULL, 
    alert_id INTEGER NOT NULL, 
    event_type VARCHAR(50) NOT NULL, 
    payload JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(alert_id) REFERENCES alerts (id) ON DELETE CASCADE
);

CREATE INDEX ix_alert_events_alert_created ON alert_events (alert_id, created_at);

UPDATE alembic_version SET version_num='0021' WHERE alembic_version.version_num = '0020';

-- Running upgrade 0021 -> 0022

CREATE TABLE schedules (
    id SERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    research_id INTEGER NOT NULL, 
    schedule_type VARCHAR(20) NOT NULL, 
    cron_expression VARCHAR(100), 
    models JSON NOT NULL, 
    query TEXT, 
    retry_policy JSON NOT NULL, 
    is_enabled BOOLEAN NOT NULL, 
    next_run_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    last_run_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_schedules_enabled_next_run ON schedules (is_enabled, next_run_at);

CREATE TABLE schedule_executions (
    id SERIAL NOT NULL, 
    schedule_id INTEGER NOT NULL, 
    research_id INTEGER, 
    status VARCHAR(20) NOT NULL, 
    attempts INTEGER NOT NULL, 
    error TEXT, 
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(schedule_id) REFERENCES schedules (id) ON DELETE CASCADE
);

CREATE INDEX ix_schedule_executions_schedule_started ON schedule_executions (schedule_id, started_at);

CREATE UNIQUE INDEX uq_schedule_executions_one_running ON schedule_executions (schedule_id) WHERE status = 'RUNNING';

CREATE TABLE schedule_history (
    id SERIAL NOT NULL, 
    execution_id INTEGER NOT NULL, 
    attempt INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    research_id INTEGER, 
    error TEXT, 
    retry_delay_seconds FLOAT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    finished_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(execution_id) REFERENCES schedule_executions (id) ON DELETE CASCADE
);

CREATE INDEX ix_schedule_history_execution_attempt ON schedule_history (execution_id, attempt);

UPDATE alembic_version SET version_num='0022' WHERE alembic_version.version_num = '0021';

-- Running upgrade 0022 -> 0023

CREATE TABLE baselines (
    id SERIAL NOT NULL, 
    entity_id UUID NOT NULL, 
    research_id INTEGER NOT NULL, 
    update_policy VARCHAR(30) NOT NULL, 
    thresholds JSON NOT NULL, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (entity_id)
);

CREATE TABLE baseline_snapshots (
    id SERIAL NOT NULL, 
    baseline_id INTEGER NOT NULL, 
    research_id INTEGER NOT NULL, 
    visibility FLOAT NOT NULL, 
    mention FLOAT NOT NULL, 
    recommendation FLOAT NOT NULL, 
    citation FLOAT NOT NULL, 
    coverage FLOAT NOT NULL, 
    confidence FLOAT NOT NULL, 
    reason VARCHAR(50) NOT NULL, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(baseline_id) REFERENCES baselines (id) ON DELETE CASCADE
);

CREATE INDEX ix_baseline_snapshots_baseline_created ON baseline_snapshots (baseline_id, created_at);

CREATE TABLE regression_events (
    id SERIAL NOT NULL, 
    baseline_id INTEGER NOT NULL, 
    baseline_snapshot_id INTEGER NOT NULL, 
    current_research_id INTEGER NOT NULL, 
    metric VARCHAR(30) NOT NULL, 
    baseline_value FLOAT NOT NULL, 
    current_value FLOAT NOT NULL, 
    delta FLOAT NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(baseline_id) REFERENCES baselines (id) ON DELETE CASCADE, 
    FOREIGN KEY(baseline_snapshot_id) REFERENCES baseline_snapshots (id) ON DELETE CASCADE
);

CREATE INDEX ix_regression_events_baseline_created ON regression_events (baseline_id, created_at);

CREATE INDEX ix_regression_events_snapshot_id ON regression_events (baseline_snapshot_id);

UPDATE alembic_version SET version_num='0023' WHERE alembic_version.version_num = '0022';

-- Running upgrade 0023 -> 0024

CREATE TABLE graph_snapshots (
    id SERIAL NOT NULL, 
    structure_version VARCHAR(50) NOT NULL, 
    node_count INTEGER NOT NULL, 
    edge_count INTEGER NOT NULL, 
    build_metadata JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_graph_snapshots_created ON graph_snapshots (created_at);

CREATE TABLE graph_nodes (
    id SERIAL NOT NULL, 
    snapshot_id INTEGER NOT NULL, 
    external_id VARCHAR(300) NOT NULL, 
    name VARCHAR(500) NOT NULL, 
    canonical_name VARCHAR(500) NOT NULL, 
    node_type VARCHAR(100) NOT NULL, 
    confidence FLOAT NOT NULL, 
    aliases JSON NOT NULL, 
    properties JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(snapshot_id) REFERENCES graph_snapshots (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_graph_nodes_snapshot_external ON graph_nodes (snapshot_id, external_id);

CREATE INDEX ix_graph_nodes_snapshot_type ON graph_nodes (snapshot_id, node_type);

CREATE TABLE graph_edges (
    id SERIAL NOT NULL, 
    snapshot_id INTEGER NOT NULL, 
    source_node_id INTEGER NOT NULL, 
    target_node_id INTEGER NOT NULL, 
    edge_type VARCHAR(100) NOT NULL, 
    confidence FLOAT NOT NULL, 
    properties JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(snapshot_id) REFERENCES graph_snapshots (id) ON DELETE CASCADE, 
    FOREIGN KEY(source_node_id) REFERENCES graph_nodes (id) ON DELETE CASCADE, 
    FOREIGN KEY(target_node_id) REFERENCES graph_nodes (id) ON DELETE CASCADE
);

CREATE INDEX ix_graph_edges_snapshot_type ON graph_edges (snapshot_id, edge_type);

CREATE UNIQUE INDEX uq_graph_edges_snapshot_nodes_type ON graph_edges (snapshot_id, source_node_id, target_node_id, edge_type);

UPDATE alembic_version SET version_num='0024' WHERE alembic_version.version_num = '0023';

-- Running upgrade 0024 -> 0025

CREATE TABLE canonical_entities (
    id SERIAL NOT NULL, 
    canonical_name VARCHAR(500) NOT NULL, 
    normalized_name VARCHAR(500) NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_canonical_entities_type_normalized ON canonical_entities (entity_type, normalized_name);

CREATE TABLE entity_aliases (
    id SERIAL NOT NULL, 
    canonical_entity_id INTEGER NOT NULL, 
    alias VARCHAR(500) NOT NULL, 
    normalized_alias VARCHAR(500) NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    source VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(canonical_entity_id) REFERENCES canonical_entities (id) ON DELETE CASCADE
);

CREATE INDEX ix_entity_aliases_canonical_id ON entity_aliases (canonical_entity_id);

CREATE UNIQUE INDEX uq_entity_aliases_type_normalized ON entity_aliases (entity_type, normalized_alias);

CREATE TABLE link_candidates (
    id SERIAL NOT NULL, 
    graph_snapshot_id INTEGER NOT NULL, 
    graph_node_id INTEGER NOT NULL, 
    external_id VARCHAR(300) NOT NULL, 
    entity_name VARCHAR(500) NOT NULL, 
    normalized_name VARCHAR(500) NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    canonical_entity_id INTEGER, 
    confidence FLOAT NOT NULL, 
    match_method VARCHAR(50) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(canonical_entity_id) REFERENCES canonical_entities (id) ON DELETE SET NULL
);

CREATE INDEX ix_link_candidates_status_created ON link_candidates (status, created_at);

CREATE INDEX ix_link_candidates_snapshot_node ON link_candidates (graph_snapshot_id, graph_node_id);

CREATE TABLE link_decisions (
    id SERIAL NOT NULL, 
    candidate_id INTEGER NOT NULL, 
    decision VARCHAR(30) NOT NULL, 
    canonical_entity_id INTEGER, 
    actor VARCHAR(100) NOT NULL, 
    reason TEXT, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(candidate_id) REFERENCES link_candidates (id) ON DELETE CASCADE
);

CREATE INDEX ix_link_decisions_candidate_created ON link_decisions (candidate_id, created_at);

UPDATE alembic_version SET version_num='0025' WHERE alembic_version.version_num = '0024';

-- Running upgrade 0025 -> 0026

CREATE TABLE relationship_candidates (
    id SERIAL NOT NULL, 
    graph_snapshot_id INTEGER NOT NULL, 
    source_external_id VARCHAR(300) NOT NULL, 
    target_external_id VARCHAR(300) NOT NULL, 
    relationship_type VARCHAR(30) NOT NULL, 
    confidence FLOAT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    algorithm_version VARCHAR(50) NOT NULL, 
    integrated_snapshot_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_relationship_candidates_identity ON relationship_candidates (graph_snapshot_id, source_external_id, target_external_id, relationship_type);

CREATE INDEX ix_relationship_candidates_status_created ON relationship_candidates (status, created_at);

CREATE TABLE relationship_evidence (
    id SERIAL NOT NULL, 
    candidate_id INTEGER NOT NULL, 
    source_type VARCHAR(100) NOT NULL, 
    source_reference VARCHAR(300) NOT NULL, 
    confidence FLOAT NOT NULL, 
    payload JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(candidate_id) REFERENCES relationship_candidates (id) ON DELETE CASCADE
);

CREATE INDEX ix_relationship_evidence_candidate ON relationship_evidence (candidate_id);

CREATE UNIQUE INDEX uq_relationship_evidence_source ON relationship_evidence (candidate_id, source_type, source_reference);

CREATE TABLE relationship_decisions (
    id SERIAL NOT NULL, 
    candidate_id INTEGER NOT NULL, 
    decision VARCHAR(20) NOT NULL, 
    actor VARCHAR(100) NOT NULL, 
    reason TEXT, 
    algorithm_version VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(candidate_id) REFERENCES relationship_candidates (id) ON DELETE CASCADE
);

CREATE INDEX ix_relationship_decisions_candidate_created ON relationship_decisions (candidate_id, created_at);

UPDATE alembic_version SET version_num='0026' WHERE alembic_version.version_num = '0025';

COMMIT;

