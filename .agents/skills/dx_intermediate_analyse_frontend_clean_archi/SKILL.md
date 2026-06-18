---
name: dx_intermediate_analyse_frontend_clean_archi
description: Analyse la conformité Clean Architecture du frontend Angular selon le chapitre 14. À invoquer pour auditer la structure features/<feature>/{domain,application,infrastructure,presentation}, la règle de dépendance unidirectionnelle, l'isolation du domain vis-à-vis d'Angular/NGRX/RxJS, la place de NGRX en infrastructure/store et les anti-patterns.
metadata:
  reference: § 14 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_frontend_clean_archi

## Périmètre — § 14

Cartographier pour chaque feature de `frontend/src/app/features/<feature>/` :
- Les 4 couches `domain/`, `application/`, `infrastructure/`, `presentation/`
- La règle de dépendance (§ 14.4)
- L'isolation de NGRX en `infrastructure/store/` (§ 14.6)
- L'application de SOLID (§ 14.5)
- L'uniformité entre features (§ 14.1)
- Les tests par couche (§ 14.7)
- Les anti-patterns (§ 14.8)

## Base skills (parallélisables)

- `dx_base_analyse_frontend_archi_layers_per_feature`
- `dx_base_analyse_frontend_archi_domain_no_angular` — imports `@angular/*`, NGRX, RxJS, HttpClient dans `domain/` ?
- `dx_base_analyse_frontend_archi_application_no_framework`
- `dx_base_analyse_frontend_archi_ngrx_in_infrastructure_store` — actions/reducer/effects/selectors uniquement là
- `dx_base_analyse_frontend_archi_use_cases_granularity` — un fichier = une opération
- `dx_base_analyse_frontend_archi_ports_in_domain`
- `dx_base_analyse_frontend_archi_di_in_modules`
- `dx_base_analyse_frontend_archi_uniformity_across_features`
- `dx_base_analyse_frontend_archi_test_layers`
- `dx_base_analyse_frontend_archi_dto_not_in_store`
- `dx_base_analyse_frontend_archi_eslint_restricted_imports`

## Format de sortie

Pour chaque feature, présence/absence des 4 couches, violations de dépendance (fichier:ligne via ESLint `no-restricted-imports`), DTO HTTP qui fuitent dans le store, components qui injectent `HttpClient`, écarts d'uniformité entre features.

## Anti-patterns à signaler

1. Component qui injecte `HttpClient` directement
2. Use case qui importe NGRX
3. Modèle domain qui hérite d'`Observable` ou est `@Injectable()`
4. DTO HTTP exposé tel quel dans le store
5. Logique métier dans un component
6. Service "Manager" / "Helper" générique dans `application/`
7. Pas d'inversion de dépendance (use case qui `new` une impl HTTP)
8. Features avec structures divergentes
