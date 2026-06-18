---
name: dx_intermediate_analyse_env_vars
description: Analyse les variables d'environnement et leur scoping selon le chapitre 6. Inventaire des variables CI/CD utilisées, détection des préfixes DEV_/STAGING_/PROD_ interdits, résolutions dynamiques fragiles. À invoquer pour comprendre comment les variables sont scopées dans un projet et repérer les antipatterns.
metadata:
  reference: § 6 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_env_vars

## Périmètre

- Scanner tous les `.gitlab-ci.yml`, scripts dans `scripts/`, manifests pour
  repérer les variables utilisées
- Détecter les préfixes `DEV_`, `STAGING_`, `PROD_` (interdits, § 6.1)
- Détecter les résolutions dynamiques type `${!VAR_NAME}` (interdites)
- Vérifier que `NAMESPACE`, `INGRESS_HOST`, `KUBECONFIG_VARIABLE` etc. sont
  toujours référencés sans préfixe (le scoping GitLab fait le travail)

## Base skills (parallélisables)

- `dx_base_check_env_no_dev_staging_prod_prefix`
- `dx_base_check_env_no_dynamic_resolution`
- `dx_base_check_env_scoped_in_gitlab`

## Format de sortie

```markdown
## Analyse Variables d'environnement (§ 6)

### Variables utilisées
| Variable | Fichier(s) | Préfixée ? | Résolution dynamique ? |
|---|---|---|---|
| NAMESPACE | .gitlab-ci.yml, scripts/deploy.sh | non | non |
| DEV_DATABASE_HOST | scripts/migrate.sh | OUI (à corriger § 6.1) | non |

### Recommandations
- Migrer X variables vers le scoping GitLab natif (§ 6.4)
```
