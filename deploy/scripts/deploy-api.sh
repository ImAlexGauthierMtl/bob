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

# Resolve API directory (exposed or internal)
if [[ -d "${PROJECT_ROOT}/apis/exposed/${API_NAME}" ]]; then
    API_LAYER="exposed"
elif [[ -d "${PROJECT_ROOT}/apis/internal/${API_NAME}" ]]; then
    API_LAYER="internal"
else
    echo "Warning: API directory not found for ${API_NAME}, using default config"
    API_LAYER=""
fi

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
if [[ "${API_NAME}" == *"backend"* ]]; then
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

# Clean up stuck Helm release
RELEASE_STATUS=$(helm status "${API_NAME}" --namespace "${NAMESPACE}" -o json 2>/dev/null | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "not-found")
if [[ "${RELEASE_STATUS}" == "pending-install" || "${RELEASE_STATUS}" == "pending-upgrade" || "${RELEASE_STATUS}" == "pending-rollback" ]]; then
    echo "  Helm release stuck in '${RELEASE_STATUS}', cleaning up..."
    helm uninstall "${API_NAME}" --namespace "${NAMESPACE}" --no-hooks 2>/dev/null || true
    sleep 2
elif [[ "${RELEASE_STATUS}" == "failed" ]]; then
    echo "  Helm release in 'failed' state, will attempt upgrade..."
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

# Inject INGRESS_URL for CORS
if [[ -n "${INGRESS_URL:-}" ]]; then
    HELM_CMD="${HELM_CMD} --set env.INGRESS_URL=\"${INGRESS_URL}\""
    HELM_CMD="${HELM_CMD} --set env.CORS_ORIGINS=\"[\\\"${INGRESS_URL}\\\"]\""
fi

# Inject OTLP_URL for tracing
if [[ -n "${OTLP_URL:-}" ]]; then
    HELM_CMD="${HELM_CMD} --set env.OTLP_URL=\"${OTLP_URL}\""
fi

# Inject JWT SECRET_KEY for B4F APIs (exposed, need auth)
if [[ "${API_NAME}" == *"-b4f-api" ]]; then
    if [[ -n "${JWT_SECRET_KEY:-}" ]]; then
        echo "  Injecting SECRET_KEY for ${API_NAME}"
        HELM_CMD="${HELM_CMD} --set secrets.jwtSecret=\"${JWT_SECRET_KEY}\""
    else
        echo "  Warning: JWT_SECRET_KEY not set"
    fi
fi

# Inject backend service URLs for B4F APIs
if [[ "${API_NAME}" == *"-b4f-api" ]]; then
    echo "  Injecting backend service URLs for ${API_NAME}..."
    HELM_CMD="${HELM_CMD} \
        --set env.USER_BACKEND_API_URL=http://user-backend-api:9001 \
        --set env.CONTACT_BACKEND_API_URL=http://contact-backend-api:9002 \
        --set env.ORG_BACKEND_API_URL=http://org-backend-api:9003 \
        --set env.OPPORTUNITY_BACKEND_API_URL=http://opportunity-backend-api:9004 \
        --set env.ACTIVITY_BACKEND_API_URL=http://activity-backend-api:9005 \
        --set env.PRODUCT_BACKEND_API_URL=http://product-backend-api:9006 \
        --set env.EMAIL_BACKEND_API_URL=http://email-backend-api:9007 \
        --set env.AGENT_BACKEND_API_URL=http://agent-backend-api:9008 \
        --set env.WORKFLOW_BACKEND_API_URL=http://workflow-backend-api:9009 \
        --set env.KB_BACKEND_API_URL=http://kb-backend-api:9010 \
        --set env.USAGE_BACKEND_API_URL=http://usage-backend-api:9011"
    ROUTE_PREFIX=$(${SCRIPT_DIR}/get-api-route-prefix.sh "${API_NAME}" "${ENV}" 2>/dev/null || echo "${API_NAME}" | sed 's/-b4f-api$//')
    echo "  Injecting API_ROUTE_PREFIX=${ROUTE_PREFIX} for ${API_NAME}"
    HELM_CMD="${HELM_CMD} --set env.API_ROUTE_PREFIX=\"${ROUTE_PREFIX}\""
fi

# Add admin user env for auth-b4f-api
if [[ "${API_NAME}" == "auth-b4f-api" ]]; then
    ADMIN_EMAIL_VAL="${ADMIN_EMAIL:-${ADMIN_USERNAME:-}}"
    ADMIN_PASS_VAL="${ADMIN_PASSWORD:-}"
    ADMIN_FNAME="${ADMIN_FIRST_NAME:-Admin}"
    ADMIN_LNAME="${ADMIN_LAST_NAME:-Croo}"
    if [[ -n "${ADMIN_EMAIL_VAL}" ]] && [[ -n "${ADMIN_PASS_VAL}" ]]; then
        echo "  Injecting admin credentials for ${API_NAME}"
        HELM_CMD="${HELM_CMD} \
            --set env.ADMIN_EMAIL=\"${ADMIN_EMAIL_VAL}\" \
            --set env.ADMIN_PASSWORD=\"${ADMIN_PASS_VAL}\" \
            --set env.ADMIN_FIRST_NAME=\"${ADMIN_FNAME}\" \
            --set env.ADMIN_LAST_NAME=\"${ADMIN_LNAME}\""
    else
        echo "  Warning: ADMIN_EMAIL or ADMIN_PASSWORD not set, skipping admin seed"
    fi
fi

# Add database configuration for backend APIs
if [[ "${IS_BACKEND_API}" == "true" ]]; then
    # Use DATABASE_* vars if set, otherwise fall back to DB_* vars from .env
    DB_HOST="${DATABASE_HOST:-${DB_HOST:-postgres.tools.thesmartcrew.com}}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_NAME="${DATABASE_NAME:-${DB_NAME:-croo_digital_experience}}"
    DB_USER="${DATABASE_USER:-${DB_USER:-}}"
    DB_PASSWORD="${DATABASE_PASSWORD:-${DB_PASSWORD:-}}"

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
        DB_URL="postgresql+psycopg://${ENCODED_USER}:${ENCODED_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?sslmode=require"
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

HELM_CMD="${HELM_CMD} --wait --timeout 3m --debug"

LABEL_SELECTOR="app.kubernetes.io/component=${API_NAME}"

if eval "${HELM_CMD}"; then
    echo "Helm deployment completed"
    echo ""
    kubectl get pods -n "${NAMESPACE}" -l "${LABEL_SELECTOR}" -o wide 2>&1 || true
    echo ""
    echo "${API_NAME} deployed successfully"
else
    HELM_EXIT_CODE=$?
    echo "Helm deployment failed with exit code: ${HELM_EXIT_CODE}"
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods -n "${NAMESPACE}" -l "${LABEL_SELECTOR}" -o wide 2>&1 || true
    echo ""
    echo "=== Pod Describe (last 60 lines) ==="
    kubectl describe pods -n "${NAMESPACE}" -l "${LABEL_SELECTOR}" 2>&1 | tail -60 || true
    echo ""
    echo "=== Pod Logs ==="
    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "${LABEL_SELECTOR}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "${POD_NAME}" ]; then
        kubectl logs "${POD_NAME}" -n "${NAMESPACE}" --tail=40 2>&1 || true
    else
        echo "No pod found with label ${LABEL_SELECTOR}"
    fi
    exit ${HELM_EXIT_CODE}
fi
