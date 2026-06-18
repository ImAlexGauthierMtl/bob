---
name: dx_base_check_frontend_ngrx_no_http_outside_effects
description: Vérifie qu'aucun HttpClient n'est injecté hors des Services / effects. Les components et use cases ne parlent jamais à HTTP.
metadata:
  reference: § 3 + § 8.2
---

# dx_base_check_frontend_ngrx_no_http_outside_effects

## Actions
```bash
grep -rE "HttpClient" frontend/src/app/       | grep -vE "(\.service\.ts|\.effects\.ts|\.http\.ts)"       && echo FAIL
```
