#!/bin/bash
# Get API route prefix from gateway.yaml or use default
# The route prefix is the path segment after /api/v1/ in the ingress.

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

# Try to extract routePrefix from gateway.yaml
if [[ -f "${VALUES_FILE}" ]]; then
    ROUTE_PREFIX=$(set +o pipefail; grep -A 100 "^apiRoutes:" "${VALUES_FILE}" 2>/dev/null | \
        grep -A 50 "^  apis:" 2>/dev/null | \
        grep -A 5 "^[[:space:]]*${API_NAME}:" 2>/dev/null | \
        grep "routePrefix:" 2>/dev/null | \
        sed 's/.*routePrefix:[[:space:]]*"\([^"]*\)".*/\1/' | \
        sed "s/.*routePrefix:[[:space:]]*'\([^']*\)'.*/\1/" | \
        head -1) || true

    if [[ -n "${ROUTE_PREFIX}" ]]; then
        echo "${ROUTE_PREFIX}"
        exit 0
    fi

    ROUTE_PREFIX=$(set +o pipefail; grep -A 100 "^apiRoutes:" "${VALUES_FILE}" 2>/dev/null | \
        grep -A 50 "^  bffApis:" 2>/dev/null | \
        grep -A 5 "^[[:space:]]*${API_NAME}:" 2>/dev/null | \
        grep "routePrefix:" 2>/dev/null | \
        sed 's/.*routePrefix:[[:space:]]*"\([^"]*\)".*/\1/' | \
        sed "s/.*routePrefix:[[:space:]]*'\([^']*\)'.*/\1/" | \
        head -1) || true

    if [[ -n "${ROUTE_PREFIX}" ]]; then
        echo "${ROUTE_PREFIX}"
        exit 0
    fi
fi

# Default routePrefix based on API name
case "${API_NAME}" in
    auth-api)
        echo "auth"
        ;;
    b4f-api)
        echo "bff"
        ;;
    crm-backend-api)
        echo "crm"
        ;;
    ai-agent-api)
        echo "ai-agent"
        ;;
    communication-api)
        echo "communication"
        ;;
    platform-services-api)
        echo "platform"
        ;;
    kb-api)
        echo "kb"
        ;;
    auth-b4f-api)
        echo "auth-bff"
        ;;
    crm-b4f-api)
        echo "crm-bff"
        ;;
    ai-agent-b4f-api)
        echo "ai-agent-bff"
        ;;
    communication-b4f-api)
        echo "communication-bff"
        ;;
    platform-b4f-api)
        echo "platform-bff"
        ;;
    kb-b4f-api)
        echo "kb-bff"
        ;;
    *)
        echo "${API_NAME}" | sed 's/-api$//'
        ;;
esac
