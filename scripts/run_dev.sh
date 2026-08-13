#!/usr/bin/env bash
# Runs the development server with development settings.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py runserver "${1:-127.0.0.1:8000}"
