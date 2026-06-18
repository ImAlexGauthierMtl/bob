---
name: dx_base_check_gateway_uses_wildcard_tls
description: Vérifie que le TLS du gateway pointe vers un secret unique (le wildcard copié), pas un certificat par B4F.
metadata:
  reference: § 5.11 + § 5.7 + § 8.4
---

# dx_base_check_gateway_uses_wildcard_tls

## Actions
```bash
n=$(kubectl -n "$NAMESPACE" get ingress api-gateway \
  -o jsonpath='{.spec.tls[*].secretName}' | tr ' ' '\n' | sort -u | wc -l)
[ "$n" = "1" ] || echo "FAIL: $n secrets TLS sur le gateway (doit être 1)"

# Le secret doit exister et avoir l'annotation source
secret=$(kubectl -n "$NAMESPACE" get ingress api-gateway -o jsonpath='{.spec.tls[0].secretName}')
kubectl -n "$NAMESPACE" get secret "$secret" \
  -o jsonpath='{.metadata.annotations.gateway\.croo-dev/source}' \
  | grep -q "^cert-manager/" || echo "WARN: secret $secret pas annoté comme copié"
```
