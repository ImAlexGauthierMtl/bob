#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check/create virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

export PYTHONPATH="${SCRIPT_DIR}/../..:${SCRIPT_DIR}/../../apis:${PYTHONPATH:-}"

# Export environment variables from root .env
if [ -f "$SCRIPT_DIR/../../.env" ]; then
  set -a
  source "$SCRIPT_DIR/../../.env"
  set +a
fi

echo "Starting $(basename $SCRIPT_DIR) on port ${PORT:-8000}..."
uvicorn main:app --reload --host 0.0.0.0 --port "${PORT:-8000}"
