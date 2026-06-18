---
name: dx_intermediate_check_registry_to_k8s
description: Verdict pass/fail du câblage Harbor → K8s selon § 7 et § 8.6. Couvre robot account Harbor (rotation 90j), variables HARBOR_* protégées/masquées, job provision-registry-access par env, ServiceAccount harbor-registry-deployer avec imagePullSecrets, Deployments avec serviceAccountName, jobs build+verify, test de restart pod sans ImagePullBackOff.
metadata:
  reference: § 7 + § 8.6
---

# dx_intermediate_check_registry_to_k8s

## Checklist (§ 8.6)

- [ ] Projet Harbor créé (auto-scan + auto-sign Cosign + retention)
- [ ] Robot account `robot$<projet>+ci` (push+pull+scan:read+scan:create+artifact:read)
- [ ] `HARBOR_URL` / `HARBOR_PROJECT` / `HARBOR_ROBOT_USER` (protégée) / `HARBOR_ROBOT_TOKEN` (protégée+masquée)
- [ ] Aucune variable `DEPLOY_TOKEN_*` ni usage `CI_REGISTRY_*`
- [ ] `provision-registry-access` exécuté par environnement
- [ ] ServiceAccount `harbor-registry-deployer` + Secret `harbor-registry-cred`
- [ ] Deployments avec `serviceAccountName`
- [ ] Secret idempotent (`--dry-run=client | kubectl apply`)
- [ ] Jobs `build:<api>` → Harbor et `verify:<api>` (needs build)
- [ ] Test : suppression pod → restart sans `ImagePullBackOff`

## Base skills

- `dx_base_check_registry_harbor_primary`
- `dx_base_check_registry_robot_account`
- `dx_base_check_registry_imagepullsecrets`
- `dx_base_check_registry_harbor_proxy`
- `dx_base_check_registry_retention_policy`
- `dx_base_check_cicd_verify_job`
- `dx_base_check_cicd_harbor_cve_whitelist`

## Format

Standard § 9 : un pass/fail par règle, avec fichier:ligne pour chaque fail.
