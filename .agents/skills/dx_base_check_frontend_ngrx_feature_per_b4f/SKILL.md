---
name: dx_base_check_frontend_ngrx_feature_per_b4f
description: Vérifie qu'il existe une feature NGRX par B4F dans frontend/src/app/features/<feature>/.
metadata:
  reference: § 3.4 + § 8.2
---

# dx_base_check_frontend_ngrx_feature_per_b4f

## Actions
Croiser `apis/exposed/<name>-b4f-api` ↔ `frontend/src/app/features/<name>/`.
Toute B4F sans feature ou toute feature sans B4F = FAIL.
