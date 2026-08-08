#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
: "${ROLLBACK_IMAGE_TAG:?Set ROLLBACK_IMAGE_TAG to an immutable known-good tag}"
export IMAGE_TAG="$ROLLBACK_IMAGE_TAG"
docker compose --env-file .env -f docker-compose.yml pull backend frontend
docker compose --env-file .env -f docker-compose.yml up -d backend worker frontend nginx
curl --fail --silent --show-error "http://127.0.0.1:${EDGE_PORT:-8100}/ready"
