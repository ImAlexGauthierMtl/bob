---
name: dx_intermediate_check_frontend_ngrx
description: Verdict pass/fail de conformité du frontend Angular + NGRX au chapitre 3 et § 8.2. Couvre service par B4F, feature NGRX par B4F, absence d'injection de service dans components, HTTP exclusivement dans effects, templates en async pipe, tests E2E Playwright dans frontend/e2e hors pipeline, hook git pre-commit husky.
metadata:
  reference: § 3 + § 8.2 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_frontend_ngrx

## Périmètre — § 8.2

```
- [ ] Un service Angular par B4F
- [ ] Un feature NGRX par B4F
- [ ] Aucune injection de service dans les components
- [ ] Aucune variable statique cachant un observable
- [ ] Aucun HTTP hors des Effects
- [ ] Templates utilisent | async
- [ ] Tests E2E Playwright présents dans frontend/e2e/
- [ ] Tests E2E absents du pipeline CI
- [ ] Hook git pre-commit configuré (husky) pour @smoke sur changement frontend
- [ ] Wrapper racine run_frontend_e2e.sh présent
- [ ] Tests E2E critiques tagués @smoke
```

## Base skills (parallélisables)

- `dx_base_check_frontend_service_per_b4f`
- `dx_base_check_frontend_feature_per_b4f`
- `dx_base_check_frontend_no_service_in_component`
- `dx_base_check_frontend_no_http_outside_effects`
- `dx_base_check_frontend_template_uses_async`
- `dx_base_check_frontend_e2e_in_e2e_dir`
- `dx_base_check_frontend_e2e_not_in_ci`
- `dx_base_check_frontend_pre_commit_hook`
- `dx_base_check_frontend_no_backend_urls`

## Format de sortie

Format § 9 standard, section "Frontend NGRX".
