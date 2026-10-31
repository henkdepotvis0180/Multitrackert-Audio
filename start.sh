#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Installeer eerst de omgeving volgens README.md.' >&2
  exit 1
fi
exec .venv/bin/python -m multitrack.cli "$@"
