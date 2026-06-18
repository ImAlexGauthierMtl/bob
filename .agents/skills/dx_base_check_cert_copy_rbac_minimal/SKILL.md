---
name: dx_base_check_cert_copy_rbac_minimal
description: Vérifie que le ServiceAccount du Job de copie a un RBAC minimal : lecture limitée au secret nommé, écriture limitée au secret cible.
metadata:
  reference: § 5.11
---

# dx_base_check_cert_copy_rbac_minimal

## Actions
```bash
f=/tmp/cicd-templates/deploy/helm/gateway-chart/templates/cert-copy-rbac.yaml
[ -f "$f" ] || { echo "FAIL: cert-copy-rbac.yaml absent"; exit 1; }

# Le Role reader doit avoir resourceNames pointant sur tls.sourceSecretName
grep -A5 "name: .*-reader$" "$f" | grep -q "resourceNames" \
  || echo "FAIL: Role reader sans resourceNames (RBAC trop large)"

# Pas de wildcard "*" sur les verbs
grep -A3 "verbs:" "$f" | grep -qE 'verbs:.*\*' \
  && echo "FAIL: RBAC avec verb wildcard"
```
