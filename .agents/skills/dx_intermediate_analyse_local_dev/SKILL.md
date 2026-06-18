---
name: dx_intermediate_analyse_local_dev
description: Analyse l'environnement de développement local selon le chapitre 11 — scripts racine (run_all_apis.sh, migrate_all_apis.sh, etc.), scripts par API (run_api.sh, migrate.sh, run_tests.sh), docker-compose.yml avec postgres+pgbouncer+redis+alloy, fichier .env.example, conventions de nommage des variables (préfixe = nom de dossier en SNAKE_CASE). À invoquer pour comprendre comment un dev tourne le projet en local.
metadata:
  reference: § 11 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_local_dev

## Périmètre

- Scripts racine wrapper (§ 11.1) : `run_all_apis.sh`, `migrate_all_apis.sh`,
  `run_all_apis_tests.sh`, `run_frontend.sh`, `run_frontend_tests.sh`,
  `run_frontend_e2e.sh`
- Scripts par API (§ 11.2) : `run_api.sh`, `migrate.sh` (Backend uniquement),
  `run_tests.sh`
- `docker-compose.yml` (§ 11.3) avec services : `postgres`, `pgbouncer`
  (transaction mode), `redis`, `alloy`
- `.env.example` à la racine (§ 11.4), `.env` non commité
- Convention de nommage des variables : globales sans préfixe, API préfixées
  par nom de dossier en SNAKE_CASE
- Ports applicatifs en `<API_PREFIX>_PORT`, jamais hardcodés
- Bannissement du préfixe `AUTHENTICATION_*`

## Base skills

- `dx_base_check_local_root_wrappers`
- `dx_base_check_local_per_api_scripts`
- `dx_base_check_local_compose_services`
- `dx_base_check_local_pgbouncer_transaction_mode`
- `dx_base_check_local_env_example_present`
- `dx_base_check_local_env_not_committed`
- `dx_base_check_local_env_naming_convention`
- `dx_base_check_local_no_authentication_prefix`
- `dx_base_check_local_no_hardcoded_ports`

## Format

```markdown
## Analyse Développement local (§ 11)

### Scripts racine
| Script | Présent | Logique métier ? |
|---|---|---|
| run_all_apis.sh | ✓ | non (orchestrateur pur) |

### docker-compose
- Services : <liste>
- PgBouncer pool_mode : transaction / session / autre
- Redis présent : oui / non
- Alloy présent : oui / non

### .env
- .env.example présent : oui / non
- .env commité ? oui / non
- Variables AUTHENTICATION_* détectées : <liste>
- Ports hardcodés dans docker-compose : <liste>
```
