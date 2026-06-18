---
name: dx_base_check_local_dev_root_wrappers
description: Vérifie qu'il existe des wrappers à la racine : run.sh (lance compose), test.sh (tous tests), lint.sh.
metadata:
  reference: § 11 + § 8.9
---

# dx_base_check_local_dev_root_wrappers

## Actions
```bash
for f in run.sh test.sh lint.sh; do
  [ -x "$f" ] || echo "FAIL: $f manquant ou non exécutable"
done
```
