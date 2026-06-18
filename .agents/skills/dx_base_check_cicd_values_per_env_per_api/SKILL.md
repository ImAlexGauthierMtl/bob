---
name: dx_base_check_cicd_values_per_env_per_api
description: Vérifie qu'il existe un values yaml par couple (api, environnement) sous deploy/values/.
metadata:
  reference: § 4.2
---

# dx_base_check_cicd_values_per_env_per_api

## Actions
Pour chaque api et chaque env (dev, staging, prod) :
```bash
for api in apis/exposed/* apis/internal/*; do
  name=$(basename "$api")
  for env in dev staging prod; do
    [ -f "deploy/values/$name-$env.yaml" ] || echo "FAIL: deploy/values/$name-$env.yaml manquant"
  done
done
```
