---
name: dx_base_check_frontend_ngrx_no_service_in_component
description: Vérifie qu'aucun component n'injecte un Service directement (passage obligatoire par dispatch → effects → service).
metadata:
  reference: § 3 + § 8.2
---

# dx_base_check_frontend_ngrx_no_service_in_component

## Actions
```bash
grep -rE "constructor.*: [A-Z][a-zA-Z]+Service" frontend/src/app/features/*/presentation/       | grep -v ".facade.ts"       && echo FAIL
```
