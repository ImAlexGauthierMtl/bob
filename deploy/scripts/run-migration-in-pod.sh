#!/bin/bash
# Run Alembic migrations inside a running Kubernetes pod.
#
# Required because the managed PostgreSQL is reachable only through the
# in-cluster PgBouncer service (pgbouncer.postgresql.svc.cluster.local),
# which does not resolve from the GitLab CI runner.
#
# Usage: ./deploy/scripts/run-migration-in-pod.sh <api-name> <namespace>
#
# Requires: kubectl with a valid kubeconfig.

set -euo pipefail

API_NAME="${1:?Usage: $0 <api-name> <namespace>}"
NAMESPACE="${2:?Usage: $0 <api-name> <namespace>}"
TIMEOUT="${MIGRATION_TIMEOUT:-180}"
WAIT_READY_TIMEOUT="${WAIT_READY_TIMEOUT:-180s}"

echo "=== Running migrations for ${API_NAME} in namespace ${NAMESPACE} ==="

LABEL="app.kubernetes.io/component=${API_NAME}"

# Wait for at least one pod to become Ready so kubectl exec can attach.
echo "Waiting for a Ready pod (${LABEL}) in ${NAMESPACE} (timeout ${WAIT_READY_TIMEOUT})..."
kubectl wait --for=condition=Ready pod \
  -l "${LABEL}" \
  -n "${NAMESPACE}" \
  --timeout="${WAIT_READY_TIMEOUT}" || true

POD=$(kubectl get pods -n "${NAMESPACE}" -l "${LABEL}" \
  -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | awk '{print $1}')

if [ -z "${POD}" ]; then
  echo "ERROR: No running pod found for ${LABEL} in namespace ${NAMESPACE}"
  echo "Available pods:"
  kubectl get pods -n "${NAMESPACE}" --show-labels 2>&1 || true
  exit 1
fi

echo "Using pod: ${POD}"

# Try to autodetect the directory that contains alembic.ini; fall back to /app.
WORKDIR=$(kubectl exec -n "${NAMESPACE}" "${POD}" -- \
  python3 -c "import pathlib; print(next(pathlib.Path('/').glob('**/alembic.ini')).parent)" 2>/dev/null || true)

if [ -z "${WORKDIR}" ]; then
  WORKDIR="/app"
  echo "Could not auto-detect workdir, falling back to ${WORKDIR}"
fi

echo "Working directory: ${WORKDIR}"
echo "Running: alembic upgrade head (timeout ${TIMEOUT}s)"

kubectl exec -n "${NAMESPACE}" "${POD}" -- \
  env PYTHONPATH="${WORKDIR}:${WORKDIR}/shared" \
  timeout "${TIMEOUT}" \
  sh -c "cd ${WORKDIR} && python3 -m alembic upgrade head"

echo "=== Migrations completed successfully for ${API_NAME} ==="
