#!/usr/bin/env bash
# Creates and applies database migrations.
# Usage: scripts/migrate.sh [dev|prod]   (defaults to dev)
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate

ENV="${1:-dev}"
if [ "$ENV" = "prod" ]; then
    export DJANGO_SETTINGS_MODULE=config.settings.production
else
    export DJANGO_SETTINGS_MODULE=config.settings.development
fi

echo "==> Making migrations"
python manage.py makemigrations

echo "==> Applying migrations (${ENV})"
python manage.py migrate
