#!/usr/bin/env sh
set -eu

exec gunicorn backend.app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8001} \
  --workers ${WEB_CONCURRENCY:-1} \
  --timeout ${WEB_TIMEOUT:-120} \
  --graceful-timeout ${WEB_GRACEFUL_TIMEOUT:-40} \
  --keep-alive ${WEB_KEEPALIVE:-5} \
  --access-logfile - \
  --error-logfile -
