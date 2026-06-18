---
name: dx_base_check_gateway_https_redirect
description: Vérifie que l'Ingress gateway porte les annotations ssl-redirect: true ET force-ssl-redirect: true. HTTP en clair interdit.
metadata:
  reference: § 5.11 + § 8.4
---

# dx_base_check_gateway_https_redirect

## Actions
```bash
for a in ssl-redirect force-ssl-redirect; do
  val=$(kubectl -n "$NAMESPACE" get ingress api-gateway \
    -o jsonpath="{.metadata.annotations.nginx\.ingress\.kubernetes\.io/${a}}")
  [ "$val" = "true" ] || echo "FAIL: $a != true (got '$val')"
done
```
