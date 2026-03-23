#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}🧪 Running all API tests...${NC}"

export PYTHONPATH="$APIS_DIR:$PYTHONPATH"

PASS=0; FAIL=0; SKIP=0

for layer in exposed internal; do
  [ -d "$APIS_DIR/$layer" ] || continue
  for api_dir in "$APIS_DIR/$layer"/*/; do
    api_name=$(basename "$api_dir")
    [[ "$api_name" == "shared" || "$api_name" == "__pycache__" ]] && continue

    echo -e "${YELLOW}  → Testing $layer/$api_name${NC}"

    if [[ -f "$api_dir/run_tests.sh" ]]; then
      if bash "$api_dir/run_tests.sh"; then
        PASS=$((PASS + 1))
      else
        FAIL=$((FAIL + 1))
      fi
    else
      echo "    No run_tests.sh found, skipping."
      SKIP=$((SKIP + 1))
    fi
  done
done

echo ""
echo -e "${GREEN}✅ Tests complete: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped${NC}"
[ "$FAIL" -gt 0 ] && exit 1
exit 0
