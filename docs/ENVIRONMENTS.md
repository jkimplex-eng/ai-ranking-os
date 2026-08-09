# Environments

Development, staging and production examples live under `config/environments`. Production Compose
uses `deployment/production/.env`, which is gitignored and must be readable only by the deployment
user. Development may use SQLite and mock providers. Staging uses isolated PostgreSQL/Redis with
mock providers. Production requires PostgreSQL, Redis, authentication enforcement and a 32-byte or
longer JWT secret.

Never commit passwords, API keys, access tokens, database URLs containing credentials or production
admin credentials. Rotate a secret immediately if it appears in Git or logs.
