---
name: dx_base_check_k8s_env_names_canonical
description: Vérifie que les noms d'environnements suivent la convention (dev, staging, prod) — pas de 'preprod', 'stg', 'production' divergents.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_env_names_canonical

## Actions
```bash
ls deploy/values/ | grep -oE "(dev|staging|prod|preprod|stg|production|qa|uat)" | sort -u
```
Refuser tout ce qui n'est pas dans {dev, staging, prod}.
