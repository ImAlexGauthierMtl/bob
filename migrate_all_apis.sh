#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}🗄️  Running migrations for all backend APIs...${NC}"

export PYTHONPATH="$APIS_DIR:$PYTHONPATH"

# Only backend APIs (internal/) have migrations
for api_dir in "$APIS_DIR/internal"/*/; do
  api_name=$(basename "$api_dir")
  [[ "$api_name" == "shared" || "$api_name" == "__pycache__" ]] && continue

  echo -e "${YELLOW}  → Migrating $api_name${NC}"

  if [[ -f "$api_dir/migrate.sh" ]]; then
    bash "$api_dir/migrate.sh"
  elif [[ -d "$api_dir/alembic" ]]; then
    (cd "$api_dir" && alembic upgrade head)
  else
    echo "    No migration mechanism found, skipping."
  fi
done

echo -e "${GREEN}✅ All migrations complete${NC}"
