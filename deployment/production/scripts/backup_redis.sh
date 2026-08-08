#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
target="backups/redis-${timestamp}.rdb"
compose='docker compose --env-file .env -f docker-compose.yml'
previous=$($compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning LASTSAVE)
$compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning BGSAVE >/dev/null
while [ "$($compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning LASTSAVE)" = "$previous" ]; do sleep 1; done
container=$($compose ps -q redis)
docker cp "$container:/data/dump.rdb" "$target" >/dev/null
docker run --rm --entrypoint redis-check-rdb -v "$(pwd)/backups:/backups:ro" \
  redis:8-alpine "/backups/$(basename "$target")" >/dev/null
echo "$target"
