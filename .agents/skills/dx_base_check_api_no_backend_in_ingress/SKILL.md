---
name: dx_base_check_api_no_backend_in_ingress
description: Vérifie qu'aucune Backend API n'est exposée par l'ingress (deploy/values/*.yaml). Les Backends sont internes.
metadata:
  reference: § 2.2 + § 8.1
---

# dx_base_check_api_no_backend_in_ingress

## Règle
`ingress.enabled: true` interdit pour `*-backend-api`.

## Actions
```bash
grep -rA2 "backend-api" deploy/values/ | grep -E "ingress|host:" && echo FAIL
```
