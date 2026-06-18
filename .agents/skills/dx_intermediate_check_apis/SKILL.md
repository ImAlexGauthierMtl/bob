---
name: dx_intermediate_check_apis
description: Vérifie la conformité du chapitre 2 (Architecture des APIs deux tiers) au format pass/fail. À invoquer dans une revue pour valider B4F/Backend, event bus, accès DB, migrations Alembic et le bannissement du terme 'authentication'. Couvre la section 8.1 de la checklist consolidée.
metadata:
  reference: § 2 + § 8.1 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_apis

## Périmètre — § 8.1 de la doc

Vérifier toutes les cases de la checklist § 8.1 :

```
- [ ] Aucun *-backend-api dans apis/exposed/
- [ ] Aucun *-b4f-api dans apis/internal/
- [ ] Aucune B4F avec alembic/, modèles DB, DATABASE_URL
- [ ] Aucune Backend dans les routes ingress
- [ ] Aucune URL *-backend-api côté frontend
- [ ] Aucune API monolithique sans suffixe
- [ ] Aucun HTTP entre Backends (event bus uniquement)
- [ ] Une entité principale par Backend
- [ ] Chaque B4F mappe un domaine frontend
- [ ] B4F minimisent les allers-retours
- [ ] Tous les Backends utilisent les mêmes DB_HOST/USERNAME/PASSWORD/DATABASE/SSLMODE
- [ ] Chaque Backend possède un schéma au nom du service
- [ ] Pool SQLAlchemy : pool_size ≤ 5, max_overflow ≤ 5, pool_pre_ping=True
- [ ] Prepared statements désactivés
- [ ] Aucun metadata.create_all(), db.create_all() ou DDL au startup
- [ ] Migrations exécutées via initContainer, jamais depuis runner CI
- [ ] InitContainer migrate exécute scripts/migrate_with_lease.py
- [ ] REDIS_URL injecté dans l'initContainer migrate
- [ ] helm upgrade --wait + récupération des logs sur échec
- [ ] Stratégie RollingUpdate avec maxSurge: 1, maxUnavailable: 0
- [ ] Migrations idempotentes
- [ ] Redis présent dans docker-compose et Helm
```

## Base skills (parallélisables)

- `dx_base_check_api_tier_placement`
- `dx_base_check_api_no_db_in_b4f`
- `dx_base_check_api_no_backend_in_ingress`
- `dx_base_check_api_no_frontend_to_backend`
- `dx_base_check_api_no_http_between_backends`
- `dx_base_check_api_event_bus_redis`

### Séparation des responsabilités B4F / Backend (v1.7)

- `dx_base_check_b4f_holds_business_logic` — le B4F porte la logique d'affaire (pas un proxy 1:1)
- `dx_base_check_b4f_grouped_by_business_domain` — B4F = domaine d'affaire aligné frontend (1:1, § 3.4)
- `dx_base_check_backend_atomic_entity` — Backend = une entité atomique, pas de logique transverse
- `dx_base_check_backend_owns_infrastructure` — DB/services externes/fichiers dans le Backend uniquement

- `dx_base_check_api_naming_no_authentication`
- `dx_base_check_api_shared_db_config`
- `dx_base_check_api_schema_per_service`
- `dx_base_check_api_db_pool_size`
- `dx_base_check_api_no_prepared_statements`
- `dx_base_check_api_no_create_all_at_startup`
- `dx_base_check_api_migration_initcontainer`
- `dx_base_check_api_migration_lease`
- `dx_base_check_api_helm_wait_with_logs`
- `dx_base_check_api_rolling_update_strategy`

### Alembic strict (v1.2)

- `dx_base_check_alembic_all_ddl_in_alembic` — toute DDL via Alembic, aucun .sql artisanal
- `dx_base_check_alembic_no_manual_sql_files` — pas de init.sql / seed.sql / schema.sql
- `dx_base_check_alembic_no_create_all_in_code` — pas de metadata.create_all() dans le code
- `dx_base_check_alembic_first_revision_creates_schema` — première migration crée CREATE SCHEMA
- `dx_base_check_alembic_downgrade_not_empty` — aucun `def downgrade(): pass` ni NotImplementedError
- `dx_base_check_alembic_downgrade_symmetric` — pour chaque op.X en upgrade, l'inverse en downgrade
- `dx_base_check_alembic_ci_tests_downgrade` — CI exécute downgrade -1 && upgrade head

Lancer en parallèle via subagents quand possible.

## Format de sortie

```markdown
### Architecture APIs (§ 2)
- OK (§ 2.1) : séparation exposed/ vs internal/ respectée
- OK (§ 2.7.1) : DB partagée
- VIOLATION critique (§ 2.7.5) : apis/internal/rooms-backend-api/src/main.py ligne 42 — appel à `Base.metadata.create_all(engine)` au démarrage
- VIOLATION à corriger (§ 2.5) : apis/internal/iam-backend-api/src/auth/users.py — résidu de classe `Authentication` à renommer
- ...

### Résumé du chapitre
- Conformes : X/Y règles
- Violations critiques : Z
- Violations à corriger : W
```

## Anti-patterns

1. Marquer "OK" sans avoir lu le code — chaque OK doit pointer un fichier qui prouve.
2. Faire un seul "VIOLATION : multiples problèmes" — un fail par règle.
3. Ne pas distinguer critique vs à corriger.
