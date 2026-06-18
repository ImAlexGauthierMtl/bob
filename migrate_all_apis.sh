#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"
filter="${1:-}"

export PYTHONPATH="$APIS_DIR:${PYTHONPATH:-}"

count=0
for api_dir in "$APIS_DIR/internal"/*-backend-api/; do
  [ -d "$api_dir" ] || continue
  api_name="$(basename "$api_dir")"
  if [ -n "$filter" ] && [ "$api_name" != "$filter" ]; then
    continue
  fi
  if [ ! -x "$api_dir/migrate.sh" ]; then
    printf '[skip] %s missing migrate.sh\n' "$api_name"
    continue
  fi
  printf '[migrate] %s\n' "$api_name"
  (cd "$api_dir" && ./migrate.sh)
  count=$((count + 1))
done

printf '[migrate] completed=%s\n' "$count"
[ "$count" -gt 0 ] || exit 1
