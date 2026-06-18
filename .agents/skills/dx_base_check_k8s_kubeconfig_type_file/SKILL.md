---
name: dx_base_check_k8s_kubeconfig_type_file
description: Vérifie que les variables CI de type 'File' sont utilisées pour les kubeconfig (jamais 'Variable' string).
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_kubeconfig_type_file

## Actions
Inspecter dans GitLab UI : Settings → CI/CD → Variables. Toutes les `*_KUBECONFIG*` doivent être de type File. Documenter dans README si non vérifiable depuis le repo.
