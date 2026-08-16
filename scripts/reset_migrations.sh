#!/usr/bin/env bash
# Resets migrations for one app, or every local app, back to a single fresh
# 0001_initial - for development use when models have changed enough that
# rewriting migration history is easier than layering more migrations on.
#
# WARNING: this deletes migration files and (by default) the local SQLite
# database. It is NOT for use against a database you care about - there is
# no attempt to preserve existing data.
#
# WARNING: resetting a single app whose models other apps have a
# ForeignKey to (e.g. resetting just "branches", which "products" and
# "sales_data" reference) will break Django's migration dependency graph,
# since the dependent app's migration still points at the old, now-deleted
# migration. When in doubt, pass every affected app together (or omit
# arguments entirely to reset everything, which is always safe).
#
# Usage:
#   scripts/reset_migrations.sh                 # reset every local app (safe default)
#   scripts/reset_migrations.sh products         # reset just apps/products (only if nothing else depends on it)
#   scripts/reset_migrations.sh products branches sales_data  # reset multiple apps that reference each other together
#   scripts/reset_migrations.sh --keep-db        # reset migrations but don't touch db.sqlite3
set -euo pipefail
cd "$(dirname "$0")/.."

KEEP_DB=false
APPS=()
for arg in "$@"; do
    if [ "$arg" = "--keep-db" ]; then
        KEEP_DB=true
    else
        APPS+=("$arg")
    fi
done

if [ ${#APPS[@]} -eq 0 ]; then
    # Every local app that has its own migrations directory.
    for dir in apps/*/migrations; do
        APPS+=("$(basename "$(dirname "$dir")")")
    done
fi

ALL_APPS=()
for dir in apps/*/migrations; do
    ALL_APPS+=("$(basename "$(dirname "$dir")")")
done

RESETTING_SUBSET=false
if [ ${#APPS[@]} -lt ${#ALL_APPS[@]} ]; then
    RESETTING_SUBSET=true
fi

echo "==> This will delete migration files for: ${APPS[*]}"
if [ "$RESETTING_SUBSET" = true ]; then
    echo "    NOTE: if another app has a ForeignKey to one of these, reset that app too (see warning at top of this script)."
fi
if [ "$KEEP_DB" = false ]; then
    echo "    ...and delete db.sqlite3 (use --keep-db to skip this)."
fi
read -r -p "Continue? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted."
    exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.development}"

for app in "${APPS[@]}"; do
    dir="apps/${app}/migrations"
    if [ ! -d "$dir" ]; then
        echo "    Skipping '${app}': no migrations directory at ${dir}"
        continue
    fi
    echo "==> Resetting migrations for '${app}'"
    find "$dir" -name "*.py" ! -name "__init__.py" -delete
    find "$dir" -name "*.pyc" -delete
    [ -f "$dir/__init__.py" ] || touch "$dir/__init__.py"
done

if [ "$KEEP_DB" = false ]; then
    echo "==> Removing db.sqlite3"
    rm -f db.sqlite3
fi

echo "==> Regenerating migrations"
python manage.py makemigrations "${APPS[@]}"

echo "==> Applying migrations"
python manage.py migrate

echo "==> Done. Remember to create a superuser if the database was reset:"
echo "    scripts/createsuperuser.sh"
