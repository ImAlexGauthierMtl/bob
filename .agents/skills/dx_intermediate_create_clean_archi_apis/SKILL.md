---
name: dx_intermediate_create_clean_archi_apis
description: Génère la structure Clean Architecture d'une API Python/FastAPI conforme au chapitre 12. À invoquer quand on bootstrap une nouvelle API ou qu'on refactor une existante. Crée les 4 couches, les ports, un use case d'exemple, la DI FastAPI, les mappers, les répertoires de tests, le .importlinter et un Dockerfile minimal.
metadata:
  reference: § 12 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_clean_archi_apis

## Périmètre

Bootstrap d'une API (B4F ou Backend) avec :
- Les 4 répertoires `domain/`, `application/`, `infrastructure/`, `presentation/`
- Un use case d'exemple (`GetEntity`) et son port (`EntityRepository`)
- Le mapping Entity ↔ Model SQLAlchemy (Backend) ou Entity ↔ DTO HTTP (B4F)
- La DI FastAPI dans `presentation/deps.py`
- Une route thin adapter `presentation/api/v1/routes.py`
- Les répertoires `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Un `.importlinter` aligné sur les contrats de dépendance
- Un `pyproject.toml`, `Dockerfile`, scripts `run_api.sh` / `migrate.sh` / `run_tests.sh`

## Base skills (séquence partielle, parallélisable par couche)

1. `dx_base_create_clean_archi_directory_skeleton` (séquentiel)
2. En parallèle :
   - `dx_base_create_clean_archi_domain_example` (entity + port + exception)
   - `dx_base_create_clean_archi_application_use_case` (GetEntity)
   - `dx_base_create_clean_archi_infrastructure_repository` (impl SQLAlchemy ou httpx)
   - `dx_base_create_clean_archi_presentation_route` (thin adapter + schema)
   - `dx_base_create_clean_archi_importlinter_config`
   - `dx_base_create_clean_archi_test_skeletons`
3. `dx_base_create_clean_archi_deps_wiring` (DI dans `presentation/deps.py`, dépend des étapes 2)
4. Câblage transverse (v1.6) :
   - `dx_base_create_shared_auth_rbac_audit` (Ports `AuthorizationPort`/`AuditPort` + adapters délégant à `apis.shared`)
   - `dx_base_create_shared_python_packaging` (sources locales éditables, ni symlink ni vendoring)
   - `dx_base_create_enforce_uniform_api_structure` (si l'API doit s'aligner sur les autres)

## Différences B4F vs Backend

| Aspect | Backend | B4F |
|---|---|---|
| `infrastructure/` | `persistence/` + `messaging/` | `backends/<service>_client.py` (httpx) |
| Port impl | `SqlAlchemy<Entity>Repository` | `Http<Service>Client` |
| Alembic | Oui (`alembic/versions/`) | Non |
| Event bus | Publish/subscribe Redis | Pas de bus interne |

## Refus

- Si le nom contient `authentication` : refuser et proposer split `<x>-b4f-api` + `iam-backend-api` (cf. § 2.5)
- Si l'API n'a pas de suffixe `-b4f-api` ou `-backend-api` : refuser (cf. § 2.1)

## Format de sortie

Liste des fichiers créés + arborescence finale + commandes de vérification post-bootstrap.
