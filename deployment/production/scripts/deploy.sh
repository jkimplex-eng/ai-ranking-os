#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
COMPOSE="docker compose --env-file .env -f docker-compose.yml"
$COMPOSE config --quiet
$COMPOSE build --pull backend frontend
$COMPOSE up -d postgres redis
$COMPOSE run --rm --no-deps backend alembic -c backend/alembic.ini upgrade head
$COMPOSE up -d backend worker frontend nginx
$COMPOSE up -d --force-recreate nginx
$COMPOSE ps
curl --fail --silent --show-error "http://127.0.0.1:${EDGE_PORT:-8100}/ready"
