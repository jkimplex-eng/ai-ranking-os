#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
domain=${APP_DOMAIN:?APP_DOMAIN is required}
compose='docker compose --env-file .env -f docker-compose.yml'

curl -fsS "http://127.0.0.1:${EDGE_PORT:-8100}/ready" >/dev/null
$compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null
$compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping | grep -q PONG
disk_percent=$(df -P / | awk 'NR==2 {gsub("%", "", $5); print $5}')
test "$disk_percent" -lt 85
latest_backup=$(find backups -type f -name 'ai-ranking-*.dump' -mmin -1500 -print -quit)
test -n "$latest_backup"
if [ -f "/etc/letsencrypt/live/$domain/cert.pem" ]; then
  openssl x509 -checkend 1209600 -noout -in "/etc/letsencrypt/live/$domain/cert.pem"
fi
printf 'monitor=PASS disk_percent=%s backup=%s\n' "$disk_percent" "$latest_backup"
