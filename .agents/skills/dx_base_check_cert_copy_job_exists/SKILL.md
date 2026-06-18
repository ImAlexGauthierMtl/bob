---
name: dx_base_check_cert_copy_job_exists
description: Vérifie que le Job de copie du secret wildcard depuis cert-manager namespace existe (ou que reflector/kubed gère la copie).
metadata:
  reference: § 5.7 + § 5.11
---

# dx_base_check_cert_copy_job_exists

## Actions
```bash
# 1) Job déclaré dans gateway-chart
f=/tmp/cicd-templates/deploy/helm/gateway-chart/templates/cert-copy-job.yaml
[ -f "$f" ] || echo "FAIL: cert-copy-job.yaml absent"
grep -q "helm.sh/hook.*pre-" "$f" || echo "FAIL: Job sans hook pre-install/pre-upgrade"
grep -q "tls.sourceNamespace" "$f" || echo "FAIL: Job ne lit pas tls.sourceNamespace"

# 2) En cluster : soit le Job a tourné, soit reflector est présent
if ! kubectl -n "$NAMESPACE" get jobs -l app.kubernetes.io/component=gateway \
     -o name 2>/dev/null | grep -q cert-copy; then
    kubectl -n kube-system get deployment reflector 2>/dev/null \
      || echo "WARN: ni cert-copy job ni reflector détecté"
fi
```
