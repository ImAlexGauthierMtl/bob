#!/bin/bash
# Deploy frontend using Helm

set -euo pipefail

ENV="${1:-dev}"
NAMESPACE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
HELM_CHART="${PROJECT_ROOT}/deploy/helm/frontend-chart"

if [[ -z "${NAMESPACE}" ]]; then
    NAMESPACE=$("${SCRIPT_DIR}/get-namespace.sh" "${ENV}")
fi

CI_REGISTRY="${CI_REGISTRY:-registry.gitlab.com}"
CI_REGISTRY_IMAGE="${CI_REGISTRY_IMAGE:-${CI_REGISTRY}/alexandre/croo-digital-experience-v.2.0}"
CI_COMMIT_SHA="${CI_COMMIT_SHA:-latest}"

IMAGE_REPO="${CI_REGISTRY_IMAGE}/frontend"

echo "Deploying frontend to ${NAMESPACE}..."
echo "  Image: ${IMAGE_REPO}:${CI_COMMIT_SHA}"

VALUES_FILE="${PROJECT_ROOT}/deploy/helm/values/${ENV}/frontend.yaml"
VALUES_ARG=""
if [[ -f "${VALUES_FILE}" ]]; then
    VALUES_ARG="-f ${VALUES_FILE}"
    echo "  Using values: ${VALUES_FILE}"
fi

# Create Docker registry secret if credentials are provided
REGISTRY_SECRET_ARG=""
if [ -n "${CI_REGISTRY_USER:-}" ] && [ -n "${CI_JOB_TOKEN:-}" ] && [ -n "${CI_REGISTRY:-}" ]; then
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
fi

if [ -n "${REGISTRY_SECRET_ARG}" ]; then
    SECRET_NAME="frontend-registry-secret"
    if kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
        kubectl delete secret "${SECRET_NAME}" -n "${NAMESPACE}" --ignore-not-found=true
    fi
fi

HELM_CMD="helm upgrade --install frontend ${HELM_CHART} \
    --namespace ${NAMESPACE} \
    --create-namespace \
    --set frontend.image.repository=${IMAGE_REPO} \
    --set frontend.image.tag=${CI_COMMIT_SHA}"

if [ -n "${REGISTRY_SECRET_ARG}" ]; then
    HELM_CMD="${HELM_CMD} ${REGISTRY_SECRET_ARG}"
fi
if [ -n "${VALUES_ARG}" ]; then
    HELM_CMD="${HELM_CMD} ${VALUES_ARG}"
fi

HELM_CMD="${HELM_CMD} --wait --timeout 10m --debug"

if eval "${HELM_CMD}"; then
    echo "Frontend deployed successfully"
else
    echo "Frontend deployment failed"
    exit 1
fi
