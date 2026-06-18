---
name: dx_base_check_apis_uniform_scripts
description: Vérifie que chaque API porte les mêmes scripts standardisés : run_api.sh + run_tests.sh (toutes), migrate.sh (Backend uniquement, jamais B4F).
metadata:
  reference: § 11.2 + § 12.1
---

# dx_base_check_apis_uniform_scripts

## Actions
```bash
for api in apis/exposed/*/ apis/internal/*/; do
    [ -d "$api" ] || continue
    name=$(basename "$api")
    [ -f "$api/run_api.sh" ]   || echo "FAIL: $name manque run_api.sh"
    [ -f "$api/run_tests.sh" ] || echo "FAIL: $name manque run_tests.sh"
    case "$api" in
        apis/internal/*) [ -f "$api/migrate.sh" ] || echo "FAIL: $name (Backend) manque migrate.sh" ;;
        apis/exposed/*)  [ -f "$api/migrate.sh" ] && echo "FAIL: $name (B4F) ne doit pas avoir migrate.sh" ;;
    esac
done
```
