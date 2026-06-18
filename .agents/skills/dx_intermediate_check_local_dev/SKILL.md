---
name: dx_intermediate_check_local_dev
description: Verdict pass/fail de l'environnement de développement local selon § 11 et § 8.9. Couvre les scripts wrappers racine, les scripts par API, docker-compose avec postgres+pgbouncer transaction mode+redis+alloy, .env.example présent et .env non commité, conventions de nommage, bannissement AUTHENTICATION_*, ports en variables, fonctionnement complet depuis zéro.
metadata:
  reference: § 11 + § 8.9 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_local_dev

## Périmètre — § 8.9

```
- [ ] Scripts wrappers à la racine : run_all_apis.sh, migrate_all_apis.sh,
      run_all_apis_tests.sh, run_frontend.sh, run_frontend_tests.sh, run_frontend_e2e.sh
- [ ] Aucune logique métier dans les wrappers
- [ ] Chaque API porte run_api.sh et run_tests.sh
- [ ] Chaque Backend porte en plus migrate.sh
- [ ] Aucune B4F ne porte migrate.sh
- [ ] docker-compose.yml à la racine avec postgres + pgbouncer + redis + alloy
- [ ] PgBouncer du compose en pool_mode = transaction
- [ ] .env.example à la racine, à jour, sans secrets de prod
- [ ] .env racine non commité
- [ ] Variables globales (DB, Redis, OTel) sans préfixe ; variables API préfixées par nom de dossier en SNAKE_CASE
- [ ] Aucun AUTHENTICATION_* (banni)
- [ ] Ports applicatifs portés par <API_PREFIX>_PORT, jamais hardcodés
- [ ] docker compose up + ./migrate_all_apis.sh + ./run_all_apis.sh donne un environnement fonctionnel depuis zéro
- [ ] Compose suit les évolutions infra au même rythme que la prod
```

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

Format § 9.
