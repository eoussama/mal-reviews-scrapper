#! /bin/sh
set -eu

MAL_USER="${1:-${MAL_USER:-Eoussama}}"
if [ "$#" -gt 0 ]; then shift; fi

./scripts/clean.sh
uv run src/scrape.py "$MAL_USER" "$@"
