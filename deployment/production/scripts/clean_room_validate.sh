#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
backup=$(./scripts/backup.sh)
export COMPOSE_PROJECT_NAME=ai-ranking-os-clean-room
export EDGE_PORT=18100
compose='docker compose --env-file .env -f docker-compose.yml'
cleanup() { $compose down --volumes --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

$compose up -d postgres redis
until $compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null; do sleep 2; done
$compose exec -T postgres pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$backup"
$compose run --rm --no-deps backend alembic -c backend/alembic.ini upgrade head
$compose up -d backend worker frontend nginx
SMOKE_BASE_URL=http://127.0.0.1:18100 SMOKE_EMAIL="$ADMIN_EMAIL" SMOKE_PASSWORD="$ADMIN_PASSWORD" python3 scripts/smoke_test.py
echo 'clean_room_redeploy=PASS'
