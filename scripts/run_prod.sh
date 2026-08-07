#!/usr/bin/env bash
# Runs the app with gunicorn using production settings.
# Intended to be invoked by a process manager (systemd, supervisor, Docker CMD, etc).
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production

WORKERS="${GUNICORN_WORKERS:-$(( $(nproc 2>/dev/null || echo 2) * 2 + 1 ))}"

exec gunicorn config.wsgi:application \
    --bind "${BIND_ADDR:-0.0.0.0:8000}" \
    --workers "${WORKERS}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
