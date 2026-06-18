---
name: dx_base_check_cicd_no_hardcoded_api_names
description: Vérifie qu'aucun nom d'API n'est en dur dans la pipeline (utilisation de discover-apis.sh).
metadata:
  reference: § 4
---

# dx_base_check_cicd_no_hardcoded_api_names

## Actions
```bash
grep -E "apis/internal/[a-z-]+-backend-api|apis/exposed/[a-z-]+-b4f-api" .gitlab-ci.yml       | grep -v "discover"       && echo "WARN: nom d'API en dur"
```
