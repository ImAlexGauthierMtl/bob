---
name: dx_base_analyse_repo_topology
description: Cartographie globale du repo : liste des APIs, features frontend, fichiers de pipeline, scripts deploy, et leurs versions.
metadata:
  reference: § 1 (vue d'ensemble)
---

# dx_base_analyse_repo_topology

## Actions
```bash
echo "=== APIs ==="; ls apis/exposed/ apis/internal/
echo "=== Frontend features ==="; ls frontend/src/app/features/
echo "=== Pipeline ==="; head -30 .gitlab-ci.yml
echo "=== Helm chart version ==="; grep "ref:" .gitlab-ci.yml
```
