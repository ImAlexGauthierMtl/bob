---
name: dx_base_check_env_vars_masked
description: Vérifie que les secrets en variables CI sont marqués 'masked' (cachés dans les logs).
metadata:
  reference: § 6 + § 8.5
---

# dx_base_check_env_vars_masked

## Actions
Audit dans GitLab UI. Toute variable nommée `*_PASSWORD`, `*_SECRET`, `*_TOKEN`, `*_KEY` doit être masked + protected.
