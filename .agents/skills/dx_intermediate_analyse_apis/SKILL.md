---
name: dx_intermediate_analyse_apis
description: Analyse l'architecture des APIs d'un projet (deux tiers B4F/Backend, event bus Redis, accès DB partagé, migrations Alembic) selon le chapitre 2 de la doc d'architecture. À invoquer pour comprendre l'état d'un dossier apis/ existant, détecter les violations de séparation B4F/Backend, repérer les API monolithiques ou mal placées. Ne juge pas (cf. dx_intermediate_check_apis pour le verdict).
metadata:
  reference: § 2 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_apis

## Champ d'analyse — chapitre 2

Examiner :
- l'arborescence `apis/exposed/` (B4F) et `apis/internal/` (Backend)
- pour chaque API : présence d'`alembic/`, modèles DB, `DATABASE_URL`, clients HTTP
- l'event bus Redis (présence, contrat des événements § 2.4)
- la config DB partagée (§ 2.7.1) : `DB_HOST`, `DB_USERNAME`, `DB_DATABASE` identiques
- l'isolation par schéma (§ 2.7.2)
- le pool SQLAlchemy (§ 2.7.3) et les prepared statements
- l'initContainer migrate (§ 2.7.5) et `migrate_with_lease.py`
- le cas particulier `authentication` (§ 2.5) — bannissement du terme
- les `shared/` (§ 2.10)

## Base skills à invoquer (parallélisable)

L'agent peut soit lire directement ces base skills, soit déléguer chaque check
à un subagent via la `task` tool. Le travail se fait **en parallèle** —
les checks ne dépendent pas les uns des autres.

- `dx_base_analyse_api_tier_placement`
- `dx_base_analyse_api_dependencies`
- `dx_base_check_api_no_db_in_b4f`
- `dx_base_check_b4f_holds_business_logic`
- `dx_base_check_b4f_grouped_by_business_domain`
- `dx_base_check_backend_atomic_entity`
- `dx_base_check_backend_owns_infrastructure`
- `dx_base_check_api_no_http_between_backends`
- `dx_base_check_api_event_bus_redis`
- `dx_base_check_api_naming_no_authentication`
- `dx_base_check_api_shared_db_config`
- `dx_base_check_api_schema_per_service`
- `dx_base_check_api_db_pool_size`
- `dx_base_check_api_no_prepared_statements`
- `dx_base_check_api_no_create_all_at_startup`
- `dx_base_check_api_migration_initcontainer`
- `dx_base_check_api_migration_lease`

## Format de sortie

```markdown
## Analyse APIs (§ 2)

### Inventaire
| Nom | Tier attendu | Tier détecté | DB | Migrations | Notes |
|---|---|---|---|---|---|
| auth-b4f-api | B4F | exposed/ | non | non | OK |
| rooms-backend-api | Backend | internal/ | oui | oui | OK |

### Points méritant attention
- Le terme `authentication` apparaît dans X fichiers (cf. § 2.5)
- L'API Y est en `apis/exposed/` mais possède un dossier `alembic/` (cf. § 2.2)
- Le pool SQLAlchemy de Z est configuré avec `pool_size=20` (cf. § 2.7.3)

### Event bus
- Redis présent dans docker-compose : oui/non
- Backends qui publient : ...
- Backends qui souscrivent : ...
- Appels HTTP entre Backends détectés : ...

### Migrations
- InitContainer migrate présent : oui/non par API
- `migrate_with_lease.py` présent : oui/non
- DDL dans le code applicatif détectée : ...
```

## Anti-patterns à ne pas commettre dans cette analyse

1. Confondre `analyse` et `check` — ici on diagnostique, on ne juge pas.
2. Ignorer les `shared/` — ils ont leurs propres règles (§ 2.10).
3. Sauter les sous-section migrations / pool — c'est là que se cachent les
   incidents prod.
