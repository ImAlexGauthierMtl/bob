---
name: dx_base_check_local_dev_per_api_scripts
description: Vérifie que chaque API a run_api.sh, run_tests.sh, migrate.sh.
metadata:
  reference: § 11 + § 8.9
---

# dx_base_check_local_dev_per_api_scripts

## Actions
```bash
for d in apis/*/*/; do
  for f in run_api.sh run_tests.sh migrate.sh; do
    [ -x "$d$f" ] || echo "FAIL: $d$f manquant"
  done
done
```
