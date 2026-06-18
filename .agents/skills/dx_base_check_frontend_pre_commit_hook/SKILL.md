---
name: dx_base_check_frontend_pre_commit_hook
description: Vérifie qu'un pre-commit hook Husky exécute lint + tests unitaires + E2E rapides.
metadata:
  reference: § 3.5 + § 8.2
---

# dx_base_check_frontend_pre_commit_hook

## Actions
```bash
[ -f frontend/.husky/pre-commit ] || echo "FAIL: pre-commit absent"
grep -E "lint|test" frontend/.husky/pre-commit || echo "FAIL: pre-commit ne run pas lint+test"
```
