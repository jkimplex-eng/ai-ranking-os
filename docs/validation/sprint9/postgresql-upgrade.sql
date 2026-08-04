BEGIN;

-- Running upgrade 0032 -> 0033

CREATE TABLE auth_users (
    id SERIAL NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    password_hash VARCHAR(512) NOT NULL, 
    display_name VARCHAR(200) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    token_version INTEGER NOT NULL, 
    oauth_provider VARCHAR(100), 
    oauth_subject VARCHAR(255), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE INDEX ix_auth_users_email ON auth_users (email);

CREATE TABLE auth_sessions (
    id VARCHAR(36) NOT NULL, 
    user_id INTEGER NOT NULL, 
    family_id VARCHAR(36) NOT NULL, 
    refresh_token_hash VARCHAR(64) NOT NULL, 
    token_version INTEGER NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    replaced_by_session_id VARCHAR(36), 
    ip_address VARCHAR(64), 
    user_agent VARCHAR(512), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    last_used_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES auth_users (id) ON DELETE CASCADE, 
    UNIQUE (refresh_token_hash)
);

CREATE INDEX ix_auth_sessions_user_active ON auth_sessions (user_id, revoked_at, expires_at);

CREATE INDEX ix_auth_sessions_family ON auth_sessions (family_id);

UPDATE alembic_version SET version_num='0033' WHERE alembic_version.version_num = '0032';

-- Running upgrade 0033 -> 0034

CREATE TABLE rbac_roles (
    id SERIAL NOT NULL, 
    code VARCHAR(80) NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    description VARCHAR(500) NOT NULL, 
    is_system BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE TABLE rbac_permissions (
    id SERIAL NOT NULL, 
    resource VARCHAR(100) NOT NULL, 
    action VARCHAR(80) NOT NULL, 
    scope VARCHAR(100) NOT NULL, 
    description VARCHAR(500) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_rbac_permission UNIQUE (resource, action, scope)
);

CREATE TABLE rbac_role_permissions (
    role_id INTEGER NOT NULL, 
    permission_id INTEGER NOT NULL, 
    PRIMARY KEY (role_id, permission_id), 
    FOREIGN KEY(role_id) REFERENCES rbac_roles (id) ON DELETE CASCADE, 
    FOREIGN KEY(permission_id) REFERENCES rbac_permissions (id) ON DELETE CASCADE
);

CREATE TABLE rbac_role_inheritance (
    role_id INTEGER NOT NULL, 
    parent_role_id INTEGER NOT NULL, 
    PRIMARY KEY (role_id, parent_role_id), 
    FOREIGN KEY(role_id) REFERENCES rbac_roles (id) ON DELETE CASCADE, 
    FOREIGN KEY(parent_role_id) REFERENCES rbac_roles (id) ON DELETE CASCADE
);

CREATE TABLE rbac_user_roles (
    user_id INTEGER NOT NULL, 
    role_id INTEGER NOT NULL, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (user_id, role_id), 
    FOREIGN KEY(role_id) REFERENCES rbac_roles (id) ON DELETE CASCADE
);

CREATE INDEX ix_rbac_user_roles_user ON rbac_user_roles (user_id);

UPDATE alembic_version SET version_num='0034' WHERE alembic_version.version_num = '0033';

-- Running upgrade 0034 -> 0035

CREATE TABLE api_keys (
    id SERIAL NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    owner_id INTEGER NOT NULL, 
    prefix VARCHAR(20) NOT NULL, 
    secret_digest VARCHAR(64) NOT NULL, 
    scopes JSON NOT NULL, 
    rate_plan VARCHAR(50) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    rotated_from_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    metadata_json JSON NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (prefix)
);

CREATE INDEX ix_api_keys_owner_id ON api_keys (owner_id);

CREATE INDEX ix_api_keys_owner_active ON api_keys (owner_id, revoked_at, expires_at);

UPDATE alembic_version SET version_num='0035' WHERE alembic_version.version_num = '0034';

-- Running upgrade 0035 -> 0036

CREATE TABLE audit_events (
    id SERIAL NOT NULL, 
    actor_id VARCHAR(100) NOT NULL, 
    actor_type VARCHAR(30) NOT NULL, 
    action VARCHAR(100) NOT NULL, 
    category VARCHAR(50) NOT NULL, 
    resource VARCHAR(100) NOT NULL, 
    resource_id VARCHAR(100), 
    ip_address VARCHAR(64), 
    user_agent VARCHAR(512), 
    old_state JSON, 
    new_state JSON, 
    correlation_id VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_audit_time_action ON audit_events (created_at, action);

CREATE INDEX ix_audit_correlation ON audit_events (correlation_id);

UPDATE alembic_version SET version_num='0036' WHERE alembic_version.version_num = '0035';

-- Running upgrade 0036 -> 0037

CREATE TABLE observability_spans (
    id SERIAL NOT NULL, 
    trace_id VARCHAR(64) NOT NULL, 
    span_id VARCHAR(32) NOT NULL, 
    operation VARCHAR(200) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    duration_ms FLOAT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (span_id)
);

CREATE INDEX ix_spans_trace_started ON observability_spans (trace_id, started_at);

UPDATE alembic_version SET version_num='0037' WHERE alembic_version.version_num = '0036';

-- Running upgrade 0037 -> 0038

CREATE TABLE cache_warm_runs (
    id SERIAL NOT NULL, 
    namespace VARCHAR(100) NOT NULL, 
    items_warmed INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

UPDATE alembic_version SET version_num='0038' WHERE alembic_version.version_num = '0037';

-- Running upgrade 0038 -> 0039

CREATE TABLE rate_limit_policies (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    algorithm VARCHAR(30) NOT NULL, 
    subject_type VARCHAR(30) NOT NULL, 
    endpoint VARCHAR(200) NOT NULL, 
    "limit" INTEGER NOT NULL, 
    window_seconds INTEGER NOT NULL, 
    burst INTEGER NOT NULL, 
    enabled BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

UPDATE alembic_version SET version_num='0039' WHERE alembic_version.version_num = '0038';

-- Running upgrade 0039 -> 0040

CREATE TABLE idempotency_records (
    id SERIAL NOT NULL, 
    scope VARCHAR(200) NOT NULL, 
    key VARCHAR(100) NOT NULL, 
    request_hash VARCHAR(64) NOT NULL, 
    status_code INTEGER NOT NULL, 
    response JSON NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_idempotency_scope_key UNIQUE (scope, key)
);

CREATE TABLE dead_letter_messages (
    id SERIAL NOT NULL, 
    queue VARCHAR(100) NOT NULL, 
    payload JSON NOT NULL, 
    error VARCHAR(2000) NOT NULL, 
    attempts INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (id)
);

UPDATE alembic_version SET version_num='0040' WHERE alembic_version.version_num = '0039';

COMMIT;

