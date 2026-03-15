#!/bin/bash
# Deploy an API using Helm

set -euo pipefail

API_NAME="${1:-}"
ENV="${2:-dev}"
NAMESPACE="${3:-}"

if [[ -z "${API_NAME}" ]]; then
    echo "Usage: $0 <api-name> [env] [namespace]" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
HELM_CHART="${PROJECT_ROOT}/deploy/helm/api-chart"

# Get namespace if not provided
if [[ -z "${NAMESPACE}" ]]; then
    NAMESPACE=$("${SCRIPT_DIR}/get-namespace.sh" "${ENV}")
fi

# Get API port
API_PORT=$("${SCRIPT_DIR}/get-api-port.sh" "${API_NAME}")

# Get registry and image tag from environment
CI_REGISTRY="${CI_REGISTRY:-registry.gitlab.com}"
CI_REGISTRY_IMAGE="${CI_REGISTRY_IMAGE:-${CI_REGISTRY}/alexandre/croo-digital-experience-v.2.0}"
CI_COMMIT_SHA="${CI_COMMIT_SHA:-latest}"

IMAGE_NAME="${API_NAME}"
IMAGE_REPO="${CI_REGISTRY_IMAGE}/${IMAGE_NAME}"

echo "Deploying ${API_NAME} to ${NAMESPACE}..."
echo "  Image: ${IMAGE_REPO}:${CI_COMMIT_SHA}"
echo "  Port: ${API_PORT}"

# Verify Kubernetes connectivity
echo "Verifying Kubernetes connectivity..."
if ! kubectl cluster-info 2>&1; then
    echo "ERROR: Cannot connect to Kubernetes cluster"
    exit 1
fi
echo ""

# Values file path: API-specific first, then generic api-values.yaml
VALUES_FILE="${PROJECT_ROOT}/deploy/helm/values/${ENV}/${API_NAME}-values.yaml"
if [[ ! -f "${VALUES_FILE}" ]]; then
    VALUES_FILE="${PROJECT_ROOT}/deploy/helm/values/${ENV}/${API_NAME}.yaml"
fi
if [[ ! -f "${VALUES_FILE}" ]]; then
    VALUES_FILE="${PROJECT_ROOT}/deploy/helm/values/${ENV}/api-values.yaml"
fi

VALUES_ARG=""
if [[ -f "${VALUES_FILE}" ]]; then
    VALUES_ARG="-f ${VALUES_FILE}"
    echo "  Using values: ${VALUES_FILE}"
else
    echo "  Using chart defaults (no values file)"
fi

# Detect backend APIs that need PostgreSQL
IS_BACKEND_API=false
if [[ "${API_NAME}" == *"backend"* ]] || [[ "${API_NAME}" == "auth-api" ]]; then
    IS_BACKEND_API=true
    echo "  Detected backend API - PostgreSQL configuration required"
fi

# Create Docker registry secret if credentials are provided
REGISTRY_SECRET_ARG=""
if [ -n "${CI_REGISTRY_USER:-}" ] && [ -n "${CI_JOB_TOKEN:-}" ] && [ -n "${CI_REGISTRY:-}" ]; then
    echo "Creating Docker registry secret for ${CI_REGISTRY}..."
    AUTH_B64=$(echo -n "${CI_REGISTRY_USER}:${CI_JOB_TOKEN}" | base64 | tr -d '\n')
    DOCKER_CONFIG_JSON="{\"auths\":{\"${CI_REGISTRY}\":{\"username\":\"${CI_REGISTRY_USER}\",\"password\":\"${CI_JOB_TOKEN}\",\"auth\":\"${AUTH_B64}\"}}}"
    TEMP_VALUES=$(mktemp)
    ESCAPED_JSON=$(echo "${DOCKER_CONFIG_JSON}" | sed 's/"/\\"/g')
    cat > "${TEMP_VALUES}" <<EOF
imagePullSecrets:
  enabled: true
  dockerconfigjson: "${ESCAPED_JSON}"
EOF
    REGISTRY_SECRET_ARG="-f ${TEMP_VALUES}"
    trap "rm -f ${TEMP_VALUES}" EXIT
else
    echo "  Warning: CI_REGISTRY_USER or CI_JOB_TOKEN not set, imagePullSecrets disabled"
fi

# Delete existing registry secret to avoid patch conflicts
if [ -n "${REGISTRY_SECRET_ARG}" ]; then
    SECRET_NAME="${API_NAME}-registry-secret"
    if kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
        kubectl delete secret "${SECRET_NAME}" -n "${NAMESPACE}" --ignore-not-found=true
    fi
fi

# Helm upgrade/install
HELM_CMD="helm upgrade --install ${API_NAME} ${HELM_CHART} \
    --namespace ${NAMESPACE} \
    --create-namespace \
    --set api.name=${API_NAME} \
    --set api.port=${API_PORT} \
    --set api.image.repository=${IMAGE_REPO} \
    --set api.image.tag=${CI_COMMIT_SHA} \
    --set service.port=${API_PORT}"

# Inject JWT SECRET_KEY for auth-api and all BFF APIs
if [[ "${API_NAME}" == "auth-api" ]] || [[ "${API_NAME}" == *"-b4f-api" ]] || [[ "${API_NAME}" == "b4f-api" ]]; then
    if [[ -n "${JWT_SECRET_KEY:-}" ]]; then
        echo "  Injecting SECRET_KEY for ${API_NAME}"
        HELM_CMD="${HELM_CMD} --set secrets.jwtSecret=\"${JWT_SECRET_KEY}\""
    else
        echo "  Warning: JWT_SECRET_KEY not set"
    fi
fi

# Inject backend service URLs for the main BFF API
if [[ "${API_NAME}" == "b4f-api" ]]; then
    echo "  Injecting backend service URLs for ${API_NAME}..."
    HELM_CMD="${HELM_CMD} \
        --set env.AUTH_API_URL=http://auth-api:8001 \
        --set env.CRM_API_URL=http://crm-backend-api:8002 \
        --set env.AI_AGENT_API_URL=http://ai-agent-api:8003 \
        --set env.COMMUNICATION_API_URL=http://communication-api:8004 \
        --set env.PLATFORM_SERVICES_API_URL=http://platform-services-api:8005 \
        --set env.KB_API_URL=http://kb-api:8006"
fi

# Add admin user env for auth-api
if [[ "${API_NAME}" == "auth-api" ]]; then
    ENV_UPPER=$(echo "${ENV}" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    ADMIN_USERNAME="${ADMIN_USERNAME:-${!ADMIN_USERNAME_VAR:-}}"
    ADMIN_PASSWORD="${ADMIN_PASSWORD:-${!ADMIN_PASSWORD_VAR:-}}"
    if [[ -n "${ADMIN_USERNAME:-}" ]] && [[ -n "${ADMIN_PASSWORD:-}" ]]; then
        HELM_CMD="${HELM_CMD} \
            --set env.ADMIN_EMAIL=\"${ADMIN_USERNAME}\" \
            --set env.ADMIN_PASSWORD=\"${ADMIN_PASSWORD}\""
    fi
fi

# Add database configuration for backend APIs
if [[ "${IS_BACKEND_API}" == "true" ]]; then
    DB_HOST="${DATABASE_HOST:-}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_NAME="${DATABASE_NAME:-croo_digital_experience}"
    DB_USER="${DATABASE_USER:-}"
    DB_PASSWORD="${DATABASE_PASSWORD:-}"

    if [[ -n "${DB_HOST}" ]] && [[ -n "${DB_USER}" ]] && [[ -n "${DB_PASSWORD}" ]]; then
        urlencode() {
            local string="${1}"
            local strlen=${#string}
            local encoded=""
            local pos c o
            for ((pos = 0; pos < strlen; pos++)); do
                c=${string:$pos:1}
                case "$c" in
                    [-_.~a-zA-Z0-9]) o="${c}" ;;
                    *) printf -v o '%%%02x' "'$c" ;;
                esac
                encoded+="${o}"
            done
            echo "${encoded}"
        }
        ENCODED_USER=$(urlencode "${DB_USER}")
        ENCODED_PASSWORD=$(urlencode "${DB_PASSWORD}")
        DB_URL="postgresql+psycopg://${ENCODED_USER}:${ENCODED_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        echo "  Configuring PostgreSQL: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
        HELM_CMD="${HELM_CMD} --set env.DATABASE_URL=\"${DB_URL}\""
    else
        echo "  Warning: DATABASE_HOST/USER/PASSWORD not set for ${ENV}"
    fi
fi

# Add optional arguments (values first, then registry secret overrides last)
if [ -n "${VALUES_ARG}" ]; then
    HELM_CMD="${HELM_CMD} ${VALUES_ARG}"
fi
if [ -n "${REGISTRY_SECRET_ARG}" ]; then
    HELM_CMD="${HELM_CMD} ${REGISTRY_SECRET_ARG}"
fi

HELM_CMD="${HELM_CMD} --wait --timeout 10m --debug"

if eval "${HELM_CMD}"; then
    echo "Helm deployment completed"
else
    HELM_EXIT_CODE=$?
    echo "Helm deployment failed with exit code: ${HELM_EXIT_CODE}"
    echo ""
    helm status "${API_NAME}" --namespace "${NAMESPACE}" 2>&1 || true
    kubectl get pods -n "${NAMESPACE}" -l app="${API_NAME}" 2>&1 || true
    exit ${HELM_EXIT_CODE}
fi

echo ""
echo "Waiting 10 seconds for pods to stabilize..."
sleep 10

kubectl get pods -n "${NAMESPACE}" -l app="${API_NAME}" 2>&1 || true
echo ""
echo "${API_NAME} deployed successfully"
