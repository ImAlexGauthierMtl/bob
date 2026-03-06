# Template: Scripts de Run (Dev Local)

> Scripts bash pour démarrer toutes les APIs et le frontend.

## `run_all_apis.sh`

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"
SHARED_DIR="$APIS_DIR/shared"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}🚀 Starting all APIs...${NC}"

# Set PYTHONPATH for shared module
export PYTHONPATH="$APIS_DIR:$PYTHONPATH"

# Find all API directories (exclude shared)
PIDS=()
for api_dir in "$APIS_DIR"/*/; do
  api_name=$(basename "$api_dir")
  [[ "$api_name" == "shared" || "$api_name" == "__pycache__" ]] && continue

  if [[ -f "$api_dir/main.py" ]]; then
    echo -e "${YELLOW}  → Starting $api_name${NC}"
    cd "$api_dir"
    python -m uvicorn main:app --reload --host 0.0.0.0 &
    PIDS+=($!)
    cd "$SCRIPT_DIR"
  fi
done

echo -e "${GREEN}✅ ${#PIDS[@]} APIs started. PIDs: ${PIDS[*]}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all.${NC}"

trap "echo -e '${RED}Stopping...${NC}'; kill ${PIDS[*]} 2>/dev/null; exit" INT TERM
wait
```

## `run_frontend.sh`

```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/frontend"
echo "🎨 Starting frontend on http://localhost:4200"
npm run start -- --proxy-config proxy.conf.json
```

## `run_all_apis_tests.sh`

```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"
export PYTHONPATH="$APIS_DIR:$PYTHONPATH"

FAILED=0
for api_dir in "$APIS_DIR"/*/; do
  api_name=$(basename "$api_dir")
  [[ "$api_name" == "shared" || "$api_name" == "__pycache__" ]] && continue
  if [[ -d "$api_dir/tests" ]]; then
    echo "🧪 Testing $api_name..."
    cd "$api_dir" && pytest --tb=short -q || FAILED=1
    cd "$SCRIPT_DIR"
  fi
done
exit $FAILED
```

## `migrate_all_apis.sh`

```bash
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
```

## Règle : `chmod +x run_*.sh migrate_*.sh` après création.
