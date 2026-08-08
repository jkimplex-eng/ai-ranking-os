#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
compose='docker compose --env-file .env -f docker-compose.yml'

postgres_backup=$(./scripts/backup.sh)
redis_backup=$(./scripts/backup_redis.sh)
test -s "$postgres_backup"
test -s "$redis_backup"

validation_db=ai_ranking_release_restore_validation
$compose exec -T postgres dropdb -U "$POSTGRES_USER" --if-exists "$validation_db"
$compose exec -T postgres createdb -U "$POSTGRES_USER" "$validation_db"
$compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$validation_db" "/backups/$(basename "$postgres_backup")"
revision=$($compose exec -T postgres psql -U "$POSTGRES_USER" -d "$validation_db" -Atc 'select version_num from alembic_version')
test "$revision" = 0042
$compose exec -T postgres dropdb -U "$POSTGRES_USER" "$validation_db"

docker run --rm --entrypoint redis-check-rdb -v "$(pwd)/backups:/backups:ro" \
  redis:8-alpine "/backups/$(basename "$redis_backup")" >/dev/null
$compose config --quiet
$compose up -d --force-recreate backend worker frontend nginx
attempt=0
until curl -fsS "http://127.0.0.1:${EDGE_PORT:-8100}/ready" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 60 ] || { echo "Application readiness timeout" >&2; exit 1; }
  sleep 2
done
printf 'disaster_recovery=PASS postgres_revision=%s redis_rdb=PASS application_redeploy=PASS\n' "$revision"
