#!/bin/bash
# Get API route prefix for ingress gateway
# Route: /api/<prefix>/v1/<endpoint>
set -eo pipefail

API_NAME="${1:-}"
ENV="${2:-dev}"

if [[ -z "${API_NAME}" ]]; then
    echo ""
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
VALUES_FILE="${PROJECT_ROOT}/deploy/helm/values/${ENV}/gateway.yaml"

# Try gateway.yaml first
if [[ -f "${VALUES_FILE}" ]]; then
    ROUTE_PREFIX=$(grep -A 5 "^[[:space:]]*${API_NAME}:" "${VALUES_FILE}" 2>/dev/null | \
        grep "routePrefix:" 2>/dev/null | \
        sed -E 's/.*routePrefix:[[:space:]]*"?([^"]*)"?.*/\1/' | \
        head -1) || true

    if [[ -n "${ROUTE_PREFIX}" ]]; then
        echo "${ROUTE_PREFIX}"
        exit 0
    fi
fi

# Default route prefix: strip -b4f-api / -backend-api suffix
case "${API_NAME}" in
    auth-b4f-api)          echo "auth" ;;
    crm-b4f-api)           echo "crm" ;;
    ai-agent-b4f-api)      echo "ai-agent" ;;
    communication-b4f-api) echo "communication" ;;
    platform-b4f-api)      echo "platform" ;;
    kb-b4f-api)            echo "kb" ;;
    *)
        # Backend APIs are internal, but provide a fallback
        echo "${API_NAME}" | sed -E 's/-(b4f|backend)-api$//'
        ;;
esac
