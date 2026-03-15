#!/bin/bash
# Create/update API Gateway (Ingress) using Helm

set -euo pipefail

ENV="${1:-dev}"
NAMESPACE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
HELM_CHART="${PROJECT_ROOT}/deploy/helm/gateway-chart"

if [[ -z "${NAMESPACE}" ]]; then
    NAMESPACE=$("${SCRIPT_DIR}/get-namespace.sh" "${ENV}")
fi

# Discover all APIs
APIS=$("${SCRIPT_DIR}/discover-apis.sh")

VALUES_FILE="${PROJECT_ROOT}/deploy/helm/values/${ENV}/gateway.yaml"

# Extract APIs already defined in gateway.yaml to avoid duplicates
DEFINED_APIS=""
DEFINED_BFF_APIS=""
if [[ -f "${VALUES_FILE}" ]]; then
    DEFINED_APIS=$(grep -A 100 "^apiRoutes:" "${VALUES_FILE}" 2>/dev/null | \
        grep -A 50 "^  apis:" | \
        grep -E "^\s+[a-z-]+-api:" | \
        sed 's/://' | sed 's/^[[:space:]]*//' | tr '\n' ' ' || echo "")

    DEFINED_BFF_APIS=$(grep -A 100 "^apiRoutes:" "${VALUES_FILE}" 2>/dev/null | \
        grep -A 50 "^  bffApis:" | \
        grep -E "^\s+[a-z-]+-b4f-api:" | \
        sed 's/://' | sed 's/^[[:space:]]*//' | tr '\n' ' ' || echo "")
fi

# Build API routes configuration
TEMP_VALUES=$(mktemp)
cat > "${TEMP_VALUES}" << 'ROUTES_EOF'
apiRoutes:
  enabled: true
  apis:
ROUTES_EOF

# Add each API route (skip backend APIs and already-defined ones)
for api in ${APIS}; do
    if [[ "${api}" == *"-backend-"* ]]; then
        echo "  Skipping ${api} (internal backend, not exposed through gateway)"
        continue
    fi

    if echo "${DEFINED_APIS} ${DEFINED_BFF_APIS}" | grep -q "\b${api}\b"; then
        echo "  Skipping ${api} (already defined in gateway.yaml)"
        continue
    fi

    PORT=$("${SCRIPT_DIR}/get-api-port.sh" "${api}")
    ROUTE_PREFIX=$("${SCRIPT_DIR}/get-api-route-prefix.sh" "${api}" "${ENV}" 2>/dev/null || echo "${api}" | sed 's/-api$//')
    cat >> "${TEMP_VALUES}" << EOF
    ${api}:
      port: ${PORT}
      routePrefix: "${ROUTE_PREFIX}"
EOF
done

# Get ingress host from environment or use default
if [[ "${ENV}" == "dev" ]]; then
    INGRESS_HOST="${INGRESS_HOST:-app-cde-dev-01.dev.thesmartcrew.com}"
elif [[ "${ENV}" == "staging" ]]; then
    INGRESS_HOST="${INGRESS_HOST:-app-cde-dev-01.staging.thesmartcrew.com}"
elif [[ "${ENV}" == "prod" ]]; then
    INGRESS_HOST="${INGRESS_HOST:-cde.thesmartcrew.com}"
else
    INGRESS_HOST="${INGRESS_HOST:-${ENV}.cde.thesmartcrew.com}"
fi

echo "Creating/updating gateway in ${NAMESPACE}..."
echo "  Ingress host: ${INGRESS_HOST}"

# Copy TLS certificate from cert-manager namespace if needed
TLS_SECRET_NAME=""
if [[ "${ENV}" == "dev" ]]; then
    TLS_SECRET_NAME="wildcard-dev-tls"
elif [[ "${ENV}" == "staging" ]]; then
    TLS_SECRET_NAME="wildcard-staging-tls"
fi

if [[ -n "${TLS_SECRET_NAME}" ]]; then
    echo "  Checking TLS certificate (${TLS_SECRET_NAME})..."
    if ! kubectl get secret "${TLS_SECRET_NAME}" -n "${NAMESPACE}" &>/dev/null; then
        if kubectl get secret "${TLS_SECRET_NAME}" -n cert-manager &>/dev/null; then
            kubectl get secret "${TLS_SECRET_NAME}" -n cert-manager -o yaml | \
                sed "s/namespace: cert-manager/namespace: ${NAMESPACE}/" | \
                sed '/resourceVersion:/d' | \
                sed '/uid:/d' | \
                sed '/creationTimestamp:/d' | \
                kubectl apply -f -
            echo "  TLS certificate copied to ${NAMESPACE}"
        else
            echo "  Warning: TLS secret ${TLS_SECRET_NAME} not found in cert-manager namespace"
        fi
    else
        echo "  TLS certificate already exists in ${NAMESPACE}"
    fi
fi

# Helm upgrade/install
HELM_CMD=""
if [[ -f "${VALUES_FILE}" ]]; then
    echo "  Using values: ${VALUES_FILE}"
    HELM_CMD="helm upgrade --install gateway ${HELM_CHART} \
        --namespace ${NAMESPACE} \
        --create-namespace \
        --set ingress.host=${INGRESS_HOST} \
        -f ${TEMP_VALUES} \
        -f ${VALUES_FILE} \
        --wait \
        --timeout 5m"
else
    HELM_CMD="helm upgrade --install gateway ${HELM_CHART} \
        --namespace ${NAMESPACE} \
        --create-namespace \
        --set ingress.host=${INGRESS_HOST} \
        -f ${TEMP_VALUES} \
        --wait \
        --timeout 5m"
fi

set +e
HELM_OUTPUT=$(eval "${HELM_CMD}" 2>&1)
HELM_EXIT=$?
set -e

if [[ ${HELM_EXIT} -ne 0 ]]; then
    if echo "${HELM_OUTPUT}" | grep -q "has no deployed releases"; then
        echo "  Cleaning up and performing fresh install..."
        helm uninstall gateway -n "${NAMESPACE}" --ignore-not-found=true --no-hooks 2>/dev/null || true
        kubectl delete secret -n "${NAMESPACE}" -l owner=helm,name=gateway --ignore-not-found=true 2>/dev/null || true
        sleep 3
        if [[ -f "${VALUES_FILE}" ]]; then
            helm install gateway "${HELM_CHART}" \
                --namespace "${NAMESPACE}" \
                --create-namespace \
                --set ingress.host="${INGRESS_HOST}" \
                -f "${TEMP_VALUES}" \
                -f "${VALUES_FILE}" \
                --wait \
                --timeout 5m
        else
            helm install gateway "${HELM_CHART}" \
                --namespace "${NAMESPACE}" \
                --create-namespace \
                --set ingress.host="${INGRESS_HOST}" \
                -f "${TEMP_VALUES}" \
                --wait \
                --timeout 5m
        fi
        echo "  Gateway deployed successfully"
    else
        echo "Helm deployment failed:"
        echo "${HELM_OUTPUT}"
        exit ${HELM_EXIT}
    fi
else
    echo "  Gateway deployed successfully"
fi

rm -f "${TEMP_VALUES}"
