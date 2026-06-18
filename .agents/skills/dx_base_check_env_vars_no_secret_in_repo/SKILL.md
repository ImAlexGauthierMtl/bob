---
name: dx_base_check_env_vars_no_secret_in_repo
description: Vérifie qu'aucun secret en clair n'est commit (DB passwords, JWT secrets, API keys).
metadata:
  reference: § 6
---

# dx_base_check_env_vars_no_secret_in_repo

## Actions
```bash
grep -rE "(password|secret|token|api_key) *= *["'][^"']{8,}" --include="*.py" --include="*.yaml" --include="*.ts"       | grep -vE "(example|test|FAKE|REDACTED)"
git log --all -p | grep -E "BEGIN .* PRIVATE KEY"
```
