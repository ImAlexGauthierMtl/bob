---
name: dx_intermediate_check_env_vars
description: Verdict pass/fail des variables d'env selon § 6 et § 8.5. Vérifie l'absence de préfixes DEV_/STAGING_/PROD_, l'absence de résolution dynamique de préfixe, et que les variables env-spécifiques sont scopées dans GitLab (sauf dev/review en global).
metadata:
  reference: § 6 + § 8.5 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_env_vars

## Périmètre — § 8.5

```
- [ ] Aucune variable préfixée DEV_, STAGING_, PROD_
- [ ] Aucune résolution dynamique de préfixe
- [ ] Variables env-spécifiques scopées dans GitLab (sauf dev/review en global)
```

## Base skills (parallélisables)

- `dx_base_check_env_no_dev_staging_prod_prefix`
- `dx_base_check_env_no_dynamic_resolution`
- `dx_base_check_env_scoped_in_gitlab`

Format § 9.

## Détection

Grep dans le repo :

```bash
grep -REn '\b(DEV_|STAGING_|PROD_)[A-Z_]+' --include='*.yml' --include='*.sh' --include='*.yaml'
```

Toute occurrence est une violation. Liste-les avec fichier:ligne.

## Format

Section "Scoping variables" du § 9.
