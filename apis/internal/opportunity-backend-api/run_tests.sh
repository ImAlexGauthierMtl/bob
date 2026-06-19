#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check/create virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pytest pytest-cov pytest-asyncio httpx

export PYTHONPATH="${SCRIPT_DIR}/../..:${SCRIPT_DIR}/../../apis:${PYTHONPATH:-}"

if [ -n "${DATABASE_URL:-}" ] || { [ -n "${DB_HOST:-}" ] && [ -n "${DB_USERNAME:-}" ] && [ -n "${DB_DATABASE:-}" ]; }; then
  echo "[test] alembic upgrade head for $(basename "$SCRIPT_DIR")"
  alembic upgrade head

  echo "[test] alembic downgrade -1 for $(basename "$SCRIPT_DIR")"
  alembic downgrade -1

  echo "[test] alembic upgrade head after downgrade for $(basename "$SCRIPT_DIR")"
  alembic upgrade head
else
  echo "[test] skip alembic for $(basename "$SCRIPT_DIR"): DATABASE_URL/DB_* not configured"
fi

echo "[test] pytest for $(basename "$SCRIPT_DIR")"
python -m pytest tests/ -v --tb=short \
  --cov=app \
  --cov-fail-under=85 \
  --cov-report=term \
  --cov-report=xml:coverage.xml \
  --junitxml=junit.xml
