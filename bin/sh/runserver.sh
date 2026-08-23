#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PYTHON="$ROOT_DIR/.venv/bin/python"
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

if [ ! -x "$PYTHON" ]; then
	echo "Virtual environment not found. Run bin/sh/setup.sh first." >&2
	exit 1
fi

exec "$PYTHON" "$ROOT_DIR/manage.py" runserver "$HOST:$PORT" "$@"
