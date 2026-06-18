---
name: dx_intermediate_analyse_registry_to_k8s
description: Analyse le câblage Harbor → K8s selon le chapitre 7. Repère le robot account Harbor (variables HARBOR_*), le job provision-registry-access, le ServiceAccount avec imagePullSecrets, les jobs build/verify. Détecte les résidus GitLab Registry (CI_REGISTRY_*, DEPLOY_TOKEN_*) et les pulls dépendant de $CI_JOB_TOKEN au runtime.
metadata:
  reference: § 7
---

# dx_intermediate_analyse_registry_to_k8s

## Inventaire à produire

- Variables Harbor : `HARBOR_URL`, `HARBOR_PROJECT`, `HARBOR_ROBOT_USER`, `HARBOR_ROBOT_TOKEN` (protections)
- Job `provision-registry-access` : présent ? exécuté par env ?
- Secret K8s `harbor-registry-cred` + ServiceAccount `harbor-registry-deployer`
- Deployments : `serviceAccountName` configuré ?
- Jobs `build:<api>` (push Harbor) et `verify:<api>` (poll API Harbor)
- **Résidus à signaler** : `CI_REGISTRY_*`, `DEPLOY_TOKEN_*`, `.trivyignore`, scan Trivy local, pulls par `$CI_JOB_TOKEN`

## Base skills

- `dx_base_check_registry_harbor_primary`
- `dx_base_check_registry_robot_account`
- `dx_base_check_registry_imagepullsecrets`
- `dx_base_check_registry_harbor_proxy`
- `dx_base_check_registry_retention_policy`
- `dx_base_analyse` du chapitre selon besoin

## Format de sortie

Inventaire factuel (pas de verdict — c'est le rôle de check) :
- Variables présentes/absentes, protections
- Jobs détectés avec fichier:ligne
- Résidus de l'ancien câblage GitLab Registry
