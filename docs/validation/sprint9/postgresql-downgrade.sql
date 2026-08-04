BEGIN;

-- Running downgrade 0040 -> 0039

DROP TABLE dead_letter_messages;

DROP TABLE idempotency_records;

UPDATE alembic_version SET version_num='0039' WHERE alembic_version.version_num = '0040';

-- Running downgrade 0039 -> 0038

DROP TABLE rate_limit_policies;

UPDATE alembic_version SET version_num='0038' WHERE alembic_version.version_num = '0039';

-- Running downgrade 0038 -> 0037

DROP TABLE cache_warm_runs;

UPDATE alembic_version SET version_num='0037' WHERE alembic_version.version_num = '0038';

-- Running downgrade 0037 -> 0036

DROP INDEX ix_spans_trace_started;

DROP TABLE observability_spans;

UPDATE alembic_version SET version_num='0036' WHERE alembic_version.version_num = '0037';

-- Running downgrade 0036 -> 0035

DROP INDEX ix_audit_correlation;

DROP INDEX ix_audit_time_action;

DROP TABLE audit_events;

UPDATE alembic_version SET version_num='0035' WHERE alembic_version.version_num = '0036';

-- Running downgrade 0035 -> 0034

DROP INDEX ix_api_keys_owner_active;

DROP INDEX ix_api_keys_owner_id;

DROP TABLE api_keys;

UPDATE alembic_version SET version_num='0034' WHERE alembic_version.version_num = '0035';

-- Running downgrade 0034 -> 0033

DROP INDEX ix_rbac_user_roles_user;

DROP TABLE rbac_user_roles;

DROP TABLE rbac_role_inheritance;

DROP TABLE rbac_role_permissions;

DROP TABLE rbac_permissions;

DROP TABLE rbac_roles;

UPDATE alembic_version SET version_num='0033' WHERE alembic_version.version_num = '0034';

-- Running downgrade 0033 -> 0032

DROP INDEX ix_auth_sessions_family;

DROP INDEX ix_auth_sessions_user_active;

DROP TABLE auth_sessions;

DROP INDEX ix_auth_users_email;

DROP TABLE auth_users;

UPDATE alembic_version SET version_num='0032' WHERE alembic_version.version_num = '0033';

COMMIT;

