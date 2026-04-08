#!/usr/bin/env sh
set -eu

run_migrations="${RUN_MIGRATIONS:-1}"
if [ "$run_migrations" = "1" ]; then
  alembic -c alembic.ini upgrade head
fi

exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WEB_CONCURRENCY:-2} \
  --timeout ${WEB_TIMEOUT:-60} \
  --graceful-timeout ${WEB_GRACEFUL_TIMEOUT:-30} \
  --keep-alive ${WEB_KEEPALIVE:-5} \
  --access-logfile - \
  --error-logfile -
