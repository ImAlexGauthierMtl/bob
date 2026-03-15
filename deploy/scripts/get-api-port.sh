#!/bin/bash
# Get API port from docker-compose.yml or default

set -eo pipefail

API_NAME="${1:-}"
if [[ -z "${API_NAME}" ]]; then
    echo "8000"
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
DOCKER_COMPOSE="${PROJECT_ROOT}/docker-compose.yml"

# Convert k8s name back to docker-compose service name if needed
# auth-b4f-api -> auth~b4f-api (folder), but docker-compose uses different naming
SERVICE_NAME="${API_NAME}"

# Try to extract port from docker-compose.yml
if [[ -f "${DOCKER_COMPOSE}" ]]; then
    PORT=$(grep -A 20 "^  ${SERVICE_NAME}:" "${DOCKER_COMPOSE}" 2>/dev/null | \
           grep -E "^\s+- \"\$\{.*_PORT" 2>/dev/null | \
           head -1 | \
           sed -E 's/.*:\$\{.*_PORT:-([0-9]+)\}.*/\1/' 2>/dev/null || echo "")

    if [[ -n "${PORT}" ]] && [[ "${PORT}" =~ ^[0-9]+$ ]]; then
        echo "${PORT}"
        exit 0
    fi
fi

# Fallback to known ports for Croo services
case "${API_NAME}" in
    b4f-api)
        echo "8000"
        ;;
    auth-api)
        echo "8001"
        ;;
    crm-backend-api)
        echo "8002"
        ;;
    ai-agent-api)
        echo "8003"
        ;;
    communication-api)
        echo "8004"
        ;;
    platform-services-api)
        echo "8005"
        ;;
    kb-api)
        echo "8006"
        ;;
    # B4F APIs (exposed through gateway)
    auth-b4f-api)
        echo "8011"
        ;;
    crm-b4f-api)
        echo "8012"
        ;;
    ai-agent-b4f-api)
        echo "8013"
        ;;
    communication-b4f-api)
        echo "8014"
        ;;
    platform-b4f-api)
        echo "8015"
        ;;
    kb-b4f-api)
        echo "8016"
        ;;
    *)
        echo "8000"
        ;;
esac
