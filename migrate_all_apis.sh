#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"
export PYTHONPATH="$APIS_DIR:$PYTHONPATH"

for api_dir in "$APIS_DIR"/*/; do
  api_name=$(basename "$api_dir")
  [[ "$api_name" == "shared" || "$api_name" == "__pycache__" ]] && continue
  if [[ -d "$api_dir/alembic" ]]; then
    echo "📦 Migrating $api_name..."
    cd "$api_dir" && alembic upgrade head
    cd "$SCRIPT_DIR"
  fi
done
echo "✅ All migrations completed."
