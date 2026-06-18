---
name: dx_base_check_frontend_ngrx_service_per_b4f
description: Vérifie qu'il existe exactement un Angular Service par B4F (1-1 mapping) dans frontend/src/app/services/.
metadata:
  reference: § 3.4 + § 8.2
---

# dx_base_check_frontend_ngrx_service_per_b4f

## Actions
Compter apis/exposed/*-b4f-api/ et frontend services :
```bash
ls apis/exposed/ | wc -l
ls frontend/src/app/services/*.service.ts | wc -l
```
Les nombres doivent matcher et les noms correspondre.
