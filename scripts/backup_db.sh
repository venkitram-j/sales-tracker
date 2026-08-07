#!/usr/bin/env bash
# Dumps all application data to a timestamped JSON fixture under backups/.
# For PostgreSQL in production, prefer `pg_dump` for full-fidelity backups;
# this script is a portable, database-agnostic fallback using Django's
# own serialization.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source venv/bin/activate
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

mkdir -p backups
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="backups/backup_${TIMESTAMP}.json"

echo "==> Dumping data to ${OUTFILE}"
python manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude=contenttypes --exclude=auth.permission --exclude=admin.logentry --exclude=sessions.session \
    --indent 2 > "${OUTFILE}"

echo "==> Backup complete: ${OUTFILE}"
