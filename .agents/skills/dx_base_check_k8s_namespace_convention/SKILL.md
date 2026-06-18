---
name: dx_base_check_k8s_namespace_convention
description: Vérifie la convention de namespace : <project>-<env> (ex. croo-dev, croo-staging, croo-prod).
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_namespace_convention

## Actions
Inspecter les variables CI passées à `helm upgrade --namespace`. Doit matcher `<project>-<env>`.
