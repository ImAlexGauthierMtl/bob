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
pip install -q pytest pytest-cov pytest-asyncio httpx

export PYTHONPATH="${SCRIPT_DIR}/../..:${SCRIPT_DIR}/../../apis:${PYTHONPATH:-}"

echo "Running tests for $(basename $SCRIPT_DIR)..."
python -m pytest tests/ -v --tb=short --junitxml=test-results.xml || echo "No tests found or tests failed"
