#!/bin/sh
set -e

echo "⏳ Running database migrations..."
alembic upgrade head

echo "🚀 Starting API server on port ${API_PORT:-4500}..."
exec uvicorn main:app --host 0.0.0.0 --port "${API_PORT:-4500}"
