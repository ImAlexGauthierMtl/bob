---
name: dx_base_check_local_dev_env_example
description: Vérifie qu'un .env.example est présent et qu'aucun .env n'est commit.
metadata:
  reference: § 11 + § 8.9
---

# dx_base_check_local_dev_env_example

## Actions
```bash
[ -f .env.example ] || echo FAIL
git ls-files | grep -E "^\.env$" && echo "FAIL: .env committed"
grep -E "^\.env$" .gitignore || echo "FAIL: .env pas dans .gitignore"
```
