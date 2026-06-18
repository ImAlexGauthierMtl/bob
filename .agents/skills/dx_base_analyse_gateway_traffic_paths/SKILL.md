---
name: dx_base_analyse_gateway_traffic_paths
description: Cartographie le routage gateway : quel path va à quel Service, quels rewrite, quels TLS.
metadata:
  reference: § 5.11
---

# dx_base_analyse_gateway_traffic_paths

## Actions
```bash
kubectl -n "$NAMESPACE" get ingress api-gateway -o yaml | yq '
  {
    "host": .spec.rules[0].host,
    "tls": .spec.tls[0].secretName,
    "annotations": .metadata.annotations,
    "paths": [.spec.rules[0].http.paths[] | {path, backend: .backend.service.name}]
  }'
```
Produit un rapport human-readable des routes actuelles + diff vs `apis/exposed/`.
