#!/usr/bin/env sh
set -eu
python scripts/check_config.py
alembic upgrade head
exec "$@"
