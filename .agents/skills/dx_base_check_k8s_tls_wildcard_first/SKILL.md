---
name: dx_base_check_k8s_tls_wildcard_first
description: Vérifie que la stratégie TLS par défaut est 'wildcard' (réutilise un certificat *.tools.thesmartcrew.com) avant cert-manager par hôte.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_tls_wildcard_first

## Actions
Inspecter `deploy/values/*.yaml` : `tls.strategy: wildcard` doit être le default.
