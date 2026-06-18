---
name: dx_base_check_k8s_kubeconfig_indirection
description: Vérifie que KUBECONFIG est résolu via un script (resolve-kubeconfig.sh), pas en variable CI directe contenant le contenu YAML.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_kubeconfig_indirection

## Actions
```bash
grep -E "resolve-kubeconfig" .gitlab-ci.yml deploy/scripts/ || echo "WARN: indirection absente"
grep -E "KUBECONFIG:" .gitlab-ci.yml | grep -vE "\$\|/tmp" && echo "FAIL: kubeconfig en clair"
```
