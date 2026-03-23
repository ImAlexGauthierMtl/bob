#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}🚀 Starting all APIs...${NC}"

export PYTHONPATH="$APIS_DIR:$PYTHONPATH"

PIDS=()

# Discover APIs dynamically from exposed/ and internal/
for layer in exposed internal; do
  [ -d "$APIS_DIR/$layer" ] || continue
  for api_dir in "$APIS_DIR/$layer"/*/; do
    api_name=$(basename "$api_dir")
    [[ "$api_name" == "shared" || "$api_name" == "__pycache__" ]] && continue

    if [[ -f "$api_dir/run_api.sh" ]]; then
      echo -e "${YELLOW}  → Starting $layer/$api_name${NC}"
      bash "$api_dir/run_api.sh" &
      PIDS+=($!)
    elif [[ -f "$api_dir/main.py" ]]; then
      echo -e "${YELLOW}  → Starting $layer/$api_name (fallback)${NC}"
      (cd "$api_dir" && python -m uvicorn main:app --reload --host 0.0.0.0) &
      PIDS+=($!)
    fi
  done
done

echo -e "${GREEN}✅ ${#PIDS[@]} APIs started. PIDs: ${PIDS[*]}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all.${NC}"

trap "echo -e '${RED}Stopping...${NC}'; kill ${PIDS[*]} 2>/dev/null; exit" INT TERM
wait
