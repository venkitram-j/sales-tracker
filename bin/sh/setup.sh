#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VENV_DIR="$ROOT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
	python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"
"$PYTHON" "$ROOT_DIR/manage.py" migrate
