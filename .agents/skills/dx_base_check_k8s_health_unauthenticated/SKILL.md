---
name: dx_base_check_k8s_health_unauthenticated
description: Vérifie que les endpoints health sont accessibles sans authentification.
metadata:
  reference: § 5
---

# dx_base_check_k8s_health_unauthenticated

## Actions
Inspecter les routes : `/healthz/*` doit être hors de tout `Depends(get_current_user)` ou middleware auth.
