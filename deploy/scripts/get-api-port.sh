#!/bin/bash
# Get API port by name — aligned with docker-compose.yml
set -eo pipefail

API_NAME="${1:-}"
if [[ -z "${API_NAME}" ]]; then
    echo "8000"
    exit 0
fi

# B4F APIs (exposed) — ports 8001-8006
case "${API_NAME}" in
    auth-b4f-api)          echo "8001" ;;
    crm-b4f-api)           echo "8002" ;;
    ai-agent-b4f-api)      echo "8003" ;;
    communication-b4f-api) echo "8004" ;;
    platform-b4f-api)      echo "8005" ;;
    kb-b4f-api)            echo "8006" ;;

    # Backend APIs (internal) — ports 9001-9011
    user-backend-api)        echo "9001" ;;
    contact-backend-api)     echo "9002" ;;
    org-backend-api)         echo "9003" ;;
    opportunity-backend-api) echo "9004" ;;
    activity-backend-api)    echo "9005" ;;
    product-backend-api)     echo "9006" ;;
    email-backend-api)       echo "9007" ;;
    agent-backend-api)       echo "9008" ;;
    workflow-backend-api)    echo "9009" ;;
    kb-backend-api)          echo "9010" ;;
    usage-backend-api)       echo "9011" ;;

    *) echo "8000" ;;
esac
