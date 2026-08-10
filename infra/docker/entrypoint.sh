#!/bin/sh
set -eu

python -m hardening.validation

case "${1:-api}" in
  api)
    if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
      alembic -c backend/alembic.ini upgrade head
    fi
    if [ "${BOOTSTRAP_ADMIN:-false}" = "true" ]; then
      python -m scripts.create_admin
    fi
    exec uvicorn backend.app.main:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-2}" \
      --timeout-graceful-shutdown "${GRACEFUL_SHUTDOWN_SECONDS:-30}"
    ;;
  worker)
    exec python -m backend.app.worker
    ;;
  *)
    exec "$@"
    ;;
esac
