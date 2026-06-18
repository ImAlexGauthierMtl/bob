---
name: dx_base_check_k8s_namespace_from_variable
description: Vérifie que le namespace K8s n'est jamais hardcodé dans les manifestes : il vient d'une variable CI.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_namespace_from_variable

## Actions
```bash
grep -rE "namespace:" deploy/helm/*/templates/       | grep -vE "\{\{.*\.Values"       && echo "FAIL: namespace en dur"
```
