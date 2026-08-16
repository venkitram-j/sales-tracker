#!/usr/bin/env bash
# One-time project bootstrap: venv, dependencies, .env, migrations.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Creating virtual environment (venv/)"
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

echo "==> Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "==> Creating .env from .env.example"
    cp .env.example .env
    echo "    Edit .env and set a real SECRET_KEY before running in production."
fi

echo "==> Applying database migrations"
python manage.py migrate

echo "==> Setup complete."
echo "    Create an admin user with: scripts/createsuperuser.sh"
echo "    Start the dev server with: scripts/run_dev.sh"
