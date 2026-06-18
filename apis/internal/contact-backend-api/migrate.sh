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

if [ -d "alembic" ]; then
  echo "Running migrations for $(basename $SCRIPT_DIR)..."
  python -m alembic upgrade head
else
  echo "No alembic directory found for $(basename $SCRIPT_DIR), skipping."
fi
