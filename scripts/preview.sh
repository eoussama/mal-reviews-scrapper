#! /bin/sh
set -eu

MAL_USER="${1:-${MAL_USER:-Eoussama}}"
PORT="${PORT:-8000}"

if [ ! -f "out/$MAL_USER/reviews.json" ]; then
    ./scripts/run.sh "$MAL_USER"
fi

./scripts/deploy.sh "$MAL_USER"

echo "Serving the preview page on http://localhost:$PORT/"
uv run python -m http.server "$PORT" --directory build
