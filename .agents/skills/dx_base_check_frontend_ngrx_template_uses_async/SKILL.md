---
name: dx_base_check_frontend_ngrx_template_uses_async
description: Vérifie que les templates utilisent | async pour consommer les selectors, pas de .subscribe() manuel.
metadata:
  reference: § 3
---

# dx_base_check_frontend_ngrx_template_uses_async

## Actions
```bash
grep -rE "\.subscribe\(" frontend/src/app/features/*/presentation/       | grep -v ".spec.ts"       && echo "WARN: .subscribe() manuel, préférer | async"
```
