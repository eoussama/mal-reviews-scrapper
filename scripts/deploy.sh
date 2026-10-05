#! /bin/bash
set -euo pipefail

MAL_USER="${1:-${MAL_USER:-Eoussama}}"
OUTPUT_DIR="out/$MAL_USER"

if [ ! -f "$OUTPUT_DIR/reviews.json" ]; then
    echo "::error::$OUTPUT_DIR/reviews.json not found, run ./scripts/run.sh first." >&2
    exit 1
fi

latest_cache=$(ls cache/cache-*.json | sort | tail -n 1)

rm -rf build
mkdir -p build/assets

cp public/* build
cp -r "$OUTPUT_DIR/reviews" "$OUTPUT_DIR/reviews.json" build/assets
cp "$latest_cache" build/assets/cache.json

echo "Built preview page with $(basename "$latest_cache")."
