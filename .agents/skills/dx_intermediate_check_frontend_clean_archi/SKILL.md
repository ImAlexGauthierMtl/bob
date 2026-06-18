---
name: dx_intermediate_check_frontend_clean_archi
description: Vérifie pass/fail la conformité Clean Architecture du frontend Angular selon le chapitre 14. Vérification mécanique via ESLint no-restricted-imports configurée sur **/domain/** et **/application/**, plus contrôles d'arborescence, de granularité des use cases, d'isolation NGRX et anti-patterns.
metadata:
  reference: § 14 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_frontend_clean_archi

## Périmètre — § 14

```
- [ ] Chaque feature dans features/<feature>/ a domain/, application/, infrastructure/, presentation/
- [ ] domain/ ne contient AUCUN import de @angular/*, @ngrx/*, rxjs, HttpClient
- [ ] application/ ne contient AUCUN import de @angular/*, @ngrx/*, rxjs, HttpClient
- [ ] infrastructure/ ne dépend pas de presentation/
- [ ] NGRX (actions/reducer/effects/selectors) vit en infrastructure/store/ uniquement
- [ ] Un use case = un fichier dans application/use-cases/ avec une méthode execute()
- [ ] Aucun "Service" / "Manager" / "Helper" générique dans application/
- [ ] Ports dans domain/ports/ (interfaces TS)
- [ ] Ports petits (Reader/Writer séparés si méthodes >10)
- [ ] DTOs HTTP en infrastructure/api/ + mapping DTO ↔ Model
- [ ] Store stocke des Models, jamais de DTOs HTTP bruts
- [ ] Components dumb : @Input/@Output, pas d'injection HttpClient
- [ ] Smart components : dispatch + select uniquement
- [ ] Use cases injectent les Ports (pas new(), pas HttpClient direct)
- [ ] DI résolue via Angular modules (providers: useClass)
- [ ] ESLint no-restricted-imports configurée pour **/domain/** et **/application/**
- [ ] Tests par couche : domain/*.spec.ts, application/*.spec.ts, infrastructure/*.spec.ts, presentation/*.spec.ts
- [ ] Toutes les features partagent la même structure (§ 14.1)
```

## Base skills (parallélisables)

- `dx_base_check_frontend_archi_four_layers`
- `dx_base_check_frontend_archi_domain_no_framework`
- `dx_base_check_frontend_archi_application_no_framework`
- `dx_base_check_frontend_archi_infra_no_presentation`
- `dx_base_check_frontend_archi_ngrx_in_infra_store`
- `dx_base_check_frontend_archi_use_case_single_execute`
- `dx_base_check_frontend_archi_no_service_manager`
- `dx_base_check_frontend_archi_ports_in_domain`
- `dx_base_check_frontend_archi_di_via_providers`
- `dx_base_check_frontend_archi_no_http_in_components`
- `dx_base_check_frontend_archi_eslint_restricted_configured`
- `dx_base_check_frontend_archi_dto_to_model_mapping`
- `dx_base_check_frontend_archi_test_layers_present`
- `dx_base_check_frontend_archi_uniformity_across_features`

## Vérification mécanique

```bash
npx eslint 'frontend/src/app/features/**/domain/**' \
  'frontend/src/app/features/**/application/**' \
  --rule '{"no-restricted-imports":["error",{"patterns":[{"group":["@angular/*","@ngrx/*","rxjs"],"message":"Forbidden in domain/ and application/"}]}]}'
```

## Format de sortie

Pass/fail par feature + uniformité globale, format § 9.
