#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
release_sha=$(git -C ../.. rev-parse HEAD)
release_tag=$(git -C ../.. rev-parse --short=12 HEAD)
export BUILD_SHA="$release_sha" IMAGE_TAG="$release_tag"
COMPOSE="docker compose --env-file .env -f docker-compose.yml"
$COMPOSE config --quiet
$COMPOSE build --pull backend frontend
$COMPOSE up -d postgres redis
$COMPOSE run --rm --no-deps backend alembic -c backend/alembic.ini upgrade head
$COMPOSE up -d backend worker frontend nginx
$COMPOSE up -d --force-recreate nginx
$COMPOSE ps
curl --fail --silent --show-error "http://127.0.0.1:${EDGE_PORT:-8100}/ready"
sh scripts/record_release.sh .env "$release_sha" "$release_tag"
