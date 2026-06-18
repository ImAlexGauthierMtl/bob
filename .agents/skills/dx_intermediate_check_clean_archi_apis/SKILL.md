---
name: dx_intermediate_check_clean_archi_apis
description: Vérifie pass/fail la conformité Clean Architecture des APIs Python/FastAPI selon le chapitre 12. Inclut la vérification de la règle de dépendance par grep/import-linter, l'absence d'imports framework dans domain/ et application/, la granularité des use cases, l'uniformité entre APIs et l'absence des 11 anti-patterns.
metadata:
  reference: § 12 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_clean_archi_apis

## Périmètre — § 12

Vérifier chaque case :

```
- [ ] Toutes les APIs ont domain/, application/, infrastructure/, presentation/
- [ ] domain/ n'importe aucun framework (fastapi, sqlalchemy, redis, httpx, pydantic_settings)
- [ ] application/ n'importe aucun framework concret
- [ ] infrastructure/ ne dépend pas de presentation/
- [ ] Un use case = une classe avec un seul execute()
- [ ] Aucun "Service" / "Manager" / "Facade" / "Helper" générique
- [ ] domain/ports/ contient les ABCs (repositories, event_publisher)
- [ ] Ports petits (Reader/Writer séparés si >10 méthodes)
- [ ] Mockable : LSP respecté, pas de NotImplementedError
- [ ] DI résolue dans presentation/deps.py via FastAPI Depends
- [ ] Repositories injectés via constructeur, jamais new() interne
- [ ] Modèles SQLAlchemy isolés en infrastructure/persistence/models.py
- [ ] Mappers Entity ↔ Model présents
- [ ] Routes en presentation/api/v1/, thin adapters
- [ ] Schemas Pydantic dans presentation/api/v1/schemas.py
- [ ] tests/unit, tests/integration, tests/e2e présents
- [ ] Toutes les APIs partagent la même structure (§ 12.1)
- [ ] import-linter configuré (.importlinter présent)
```

## Base skills (parallélisables)

- `dx_base_check_clean_archi_four_layers_exist`
- `dx_base_check_clean_archi_domain_no_framework`
- `dx_base_check_clean_archi_application_no_framework`
- `dx_base_check_clean_archi_infra_no_presentation`
- `dx_base_check_clean_archi_use_case_single_execute`
- `dx_base_check_clean_archi_no_service_manager_helper`
- `dx_base_check_clean_archi_ports_in_domain`
- `dx_base_check_clean_archi_di_in_presentation_deps`
- `dx_base_check_clean_archi_no_raw_sql_in_repo`
- `dx_base_check_clean_archi_test_layers_present`
- `dx_base_check_clean_archi_importlinter_present`
- `dx_base_check_clean_archi_uniformity_across_apis`

### Uniformité stricte + shared (v1.6)

- `dx_base_check_apis_uniform_structure` — toutes les APIs ont exactement les mêmes couches/fichiers
- `dx_base_check_apis_uniform_scripts` — run_api.sh/run_tests.sh partout, migrate.sh Backend only
- `dx_base_check_shared_auth_rbac_centralized` — auth/RBAC via shared, pas réimplémenté ni hardcodé en route
- `dx_base_check_shared_audit_logs_centralized` — audit/logs via shared
- `dx_base_check_shared_imported_as_python_module` — pas de vendoring/lib externe
- `dx_base_check_no_symlinks_in_apis` — aucun symlink sous apis/

## Vérification mécanique

```bash
grep -RE "(fastapi|sqlalchemy|redis|httpx|pydantic_settings)" \
  src/*/domain/ src/*/application/ && exit 1
find apis/ -type l | grep . && echo "VIOLATION symlink" && exit 1
```

## Format de sortie

Tableau pass/fail par API + section globale "Uniformité (toutes APIs)".
Format § 9 du document de référence.
