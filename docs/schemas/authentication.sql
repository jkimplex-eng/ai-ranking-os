CREATE TABLE auth_users (
  id INTEGER PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  password_hash VARCHAR(512) NOT NULL,
  display_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL,
  token_version INTEGER NOT NULL,
  oauth_provider VARCHAR(100),
  oauth_subject VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX ix_auth_users_email ON auth_users(email);
CREATE TABLE auth_sessions (
  id VARCHAR(36) PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  family_id VARCHAR(36) NOT NULL,
  refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
  token_version INTEGER NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  revoked_at TIMESTAMP WITH TIME ZONE,
  replaced_by_session_id VARCHAR(36),
  ip_address VARCHAR(64),
  user_agent VARCHAR(512),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  last_used_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX ix_auth_sessions_user_active
  ON auth_sessions(user_id, revoked_at, expires_at);
CREATE INDEX ix_auth_sessions_family ON auth_sessions(family_id);
