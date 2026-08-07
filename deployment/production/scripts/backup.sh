#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
mkdir -p backups
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
target="backups/ai-ranking-${timestamp}.dump"
docker compose --env-file .env -f docker-compose.yml exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$target"
find backups -type f -name 'ai-ranking-*.dump' -mtime "+${BACKUP_RETENTION_DAYS:-14}" -delete
echo "$target"
