#!/usr/bin/env bash
# Collects static files into STATIC_ROOT for production serving via WhiteNoise.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py collectstatic --noinput
