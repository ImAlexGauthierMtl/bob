#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pytest pytest-cov pytest-asyncio httpx

export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/../..:${SCRIPT_DIR}/../../apis:${PYTHONPATH:-}"
export CDE_B4F_SURFACE=agent-control
export API_NAME=agent-control-b4f-api
export OTEL_SERVICE_NAME=agent-control-b4f-api
export AGENT_BACKEND_API_URL="${AGENT_BACKEND_API_URL:-http://agent-backend-api:9008}"
export CDE_LOCAL_AGENT_CONTROL_CAPABILITIES="${CDE_LOCAL_AGENT_CONTROL_CAPABILITIES:-}"

echo "[test] pytest for $(basename "$SCRIPT_DIR")"
python -m pytest tests/ -v --tb=short \
  --cov=app \
  --cov=agent_control_b4f_api \
  --cov-fail-under=85 \
  --cov-report=term \
  --cov-report=xml:coverage.xml \
  --junitxml=junit.xml
