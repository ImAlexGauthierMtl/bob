---
name: dx_base_check_frontend_e2e_in_e2e_dir
description: Vérifie que les tests E2E sont sous frontend/e2e/ et JAMAIS sous src/.
metadata:
  reference: § 3.5 + § 8.2
---

# dx_base_check_frontend_e2e_in_e2e_dir

## Actions
```bash
find frontend/src -name "*.e2e-spec.ts" -o -name "*.cy.ts" && echo FAIL
[ -d frontend/e2e ] || echo "FAIL: frontend/e2e/ absent"
```
