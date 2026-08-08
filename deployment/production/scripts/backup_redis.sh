#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
target="backups/redis-${timestamp}.rdb"
compose='docker compose --env-file .env -f docker-compose.yml'
$compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning BGSAVE >/dev/null
while [ "$($compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning LASTSAVE)" = "0" ]; do sleep 1; done
container=$($compose ps -q redis)
docker cp "$container:/data/dump.rdb" "$target" >/dev/null
docker run --rm -v "$(pwd)/backups:/backups:ro" redis:8-alpine redis-check-rdb "/backups/$(basename "$target")" >/dev/null
echo "$target"
