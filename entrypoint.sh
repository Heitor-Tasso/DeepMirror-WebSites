#!/bin/bash
set -e

cd /app

if [ -f "/app/.env" ]; then
    set -a
    . /app/.env
    set +a
fi

HOST="${DM_GUNICORN_BIND_HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${DM_GUNICORN_WORKERS:-1}"
THREADS="${DM_GUNICORN_THREADS:-2}"
TIMEOUT="${DM_GUNICORN_TIMEOUT:-300}"
WORKER_CLASS="${DM_GUNICORN_WORKER_CLASS:-gthread}"

echo "Starting gunicorn on ${HOST}:${PORT}..."

exec uv run gunicorn app:app \
    --bind "${HOST}:${PORT}" \
    --workers "${WORKERS}" \
    --threads "${THREADS}" \
    --timeout "${TIMEOUT}" \
    --worker-class "${WORKER_CLASS}" \
    --access-logfile - \
    --error-logfile -
