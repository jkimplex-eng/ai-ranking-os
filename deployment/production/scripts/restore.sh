#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
: "${1:?Usage: restore.sh backups/file.dump}"
backup=$1
test -f "$backup"
set -a; . ./.env; set +a
docker compose --env-file .env -f docker-compose.yml exec -T postgres pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$backup"
docker compose --env-file .env -f docker-compose.yml run --rm --no-deps backend alembic -c backend/alembic.ini upgrade head
