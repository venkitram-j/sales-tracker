#!/usr/bin/env bash
# Creates a Django superuser (interactive - prompts for email/password).
# Username is auto-derived from email; you will not be asked for one.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py createsuperuser
