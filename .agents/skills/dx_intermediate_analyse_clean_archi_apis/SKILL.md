---
name: dx_intermediate_analyse_clean_archi_apis
description: Analyse la conformité Clean Architecture des APIs Python/FastAPI selon le chapitre 12. À invoquer pour auditer la structure interne d'une API (domain/application/infrastructure/presentation), la règle de dépendance unidirectionnelle, le respect de SOLID, l'uniformité entre APIs et les anti-patterns. Inclut la vérification mécanique via grep et import-linter.
metadata:
  reference: § 12 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_clean_archi_apis

## Périmètre — § 12 de la doc

Cartographier pour chaque API du dépôt :
- Les quatre couches `domain/`, `application/`, `infrastructure/`, `presentation/`
- Le respect de la **règle de dépendance unidirectionnelle** (§ 12.3)
- L'application de **SOLID** (§ 12.4)
- L'**uniformité** entre toutes les APIs (§ 12.1)
- Les anti-patterns (§ 12.5)

## Base skills (parallélisables via subagents)

- `dx_base_analyse_clean_archi_layers_presence` — chaque API a-t-elle les 4 répertoires ?
- `dx_base_analyse_clean_archi_domain_purity` — imports framework dans `domain/` ?
- `dx_base_analyse_clean_archi_application_purity` — imports framework dans `application/` ?
- `dx_base_analyse_clean_archi_infrastructure_no_presentation` — `infrastructure/` ne dépend pas de `presentation/`
- `dx_base_analyse_clean_archi_use_cases_granularity` — un use case = un `execute()` ?
- `dx_base_analyse_clean_archi_ports_present` — `domain/ports/` défini ?
- `dx_base_analyse_clean_archi_di_via_depends` — DI résolue dans `presentation/deps.py` ?
- `dx_base_analyse_clean_archi_uniformity` — toutes les APIs partagent la même arborescence ?
- `dx_base_analyse_clean_archi_b4f_specifics` — B4F : `infrastructure/backends/` clients HTTP ?
- `dx_base_analyse_clean_archi_test_layers` — tests/unit, integration, e2e présents ?

## Format de sortie

Pour chaque API, produire :
- Présence/absence des 4 couches
- Liste des violations de la règle de dépendance (fichier:ligne)
- Use cases mal granularisés (Services fourre-tout, méthodes multiples)
- Ports manquants ou couplés à l'implémentation
- Écarts d'uniformité entre APIs (diff structurel)

## Anti-patterns à signaler

1. Modèle SQLAlchemy renvoyé directement par une route
2. Use case appelant `session.execute()` directement
3. Routes contenant de la logique métier
4. Entité héritant de `BaseModel` ou `DeclarativeBase`
5. `application/services/manager.py` générique
6. `repository.execute_raw_query(sql)`
7. `utils.py` dans `domain/` ou `application/`
8. Pydantic schema importé dans `domain/`
9. Configuration lue depuis `domain/` ou `application/`
10. APIs avec arborescences divergentes
