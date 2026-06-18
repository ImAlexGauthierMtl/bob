---
name: dx_base_check_api_tier_placement
description: Vérifie que les B4F sont sous apis/exposed/ et les Backends sous apis/internal/. Aucun *-backend-api dans exposed/, aucun *-b4f-api dans internal/.
metadata:
  reference: § 2.1 + § 8.1
---

# dx_base_check_api_tier_placement

## Règle
apis/exposed/*-b4f-api/ uniquement ; apis/internal/*-backend-api/ uniquement.

## Actions
```bash
ls apis/exposed/ | grep -E "backend-api$" && echo FAIL || true
ls apis/internal/ | grep -E "b4f-api$" && echo FAIL || true
ls apis/internal/ apis/exposed/ | grep -vE "(b4f|backend)-api$" | grep -v "^$" && echo "FAIL: API sans suffixe"
```

## Sortie
PASS ou liste des APIs mal placées.
