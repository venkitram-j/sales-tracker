#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
	echo "Virtual environment not found. Run bin/sh/setup.sh first." >&2
	exit 1
fi

"$PYTHON" "$ROOT_DIR/manage.py" collectstatic --noinput "$@"
