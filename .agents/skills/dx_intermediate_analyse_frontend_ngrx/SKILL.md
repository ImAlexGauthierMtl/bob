---
name: dx_intermediate_analyse_frontend_ngrx
description: Analyse l'architecture du frontend Angular + NGRX selon le chapitre 3 de la doc. Inventaire des features de store, services par B4F, effects, components, tests E2E Playwright. À invoquer pour comprendre comment le frontend est structuré, repérer les antipatterns NGRX (HTTP hors effects, services injectés dans components, etc.). Ne juge pas (cf. check pour le verdict).
metadata:
  reference: § 3 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_frontend_ngrx

## Périmètre

Examiner `frontend/` :
- mapping feature ↔ B4F (§ 3.4) — un store feature par B4F
- structure `store/`, `services/`, `pages/`, `components/`
- flux : template (async pipe) ← Store.select | Component.dispatch → Action → Effect → Service → B4F
- patterns interdits (§ 3.6) : service injecté dans component, variable statique cachant un observable, HTTP hors effects
- tests E2E Playwright (§ 3.8) — dossier `frontend/e2e/`, **absents** du pipeline CI
- pre-commit hook (husky) sur changement frontend

## Base skills

- `dx_base_analyse_frontend_features`
- `dx_base_check_frontend_service_per_b4f`
- `dx_base_check_frontend_feature_per_b4f`
- `dx_base_check_frontend_no_service_in_component`
- `dx_base_check_frontend_no_http_outside_effects`
- `dx_base_check_frontend_template_uses_async`
- `dx_base_check_frontend_e2e_in_e2e_dir`
- `dx_base_check_frontend_e2e_not_in_ci`
- `dx_base_check_frontend_pre_commit_hook`
- `dx_base_check_frontend_no_backend_urls`

Parallélisable.

## Format de sortie

```markdown
## Analyse Frontend NGRX (§ 3)

### Inventaire features ↔ B4F
| Feature store | Service Angular | B4F cible | Effects | Selectors |
|---|---|---|---|---|
| auth | AuthService | auth-b4f-api | oui | oui |

### Antipatterns détectés
- Component X injecte ClientsService au lieu de passer par le store
- HTTP direct dans ngOnInit de Y

### Tests E2E
- Dossier frontend/e2e/ : présent / absent
- Présence dans le pipeline CI : oui / non (doit être non)
- Hook husky pre-commit : présent / absent
- Tag @smoke pour les tests critiques : présent / absent
```
