---
name: dx_base_check_alembic_ci_tests_downgrade
description: Vérifie que la pipeline de chaque Backend exécute en CI : alembic downgrade -1 && alembic upgrade head. Garantit que le downgrade fonctionne réellement.
metadata:
  reference: § 2.7.5
---

# dx_base_check_alembic_ci_tests_downgrade

## Règle
Le downgrade doit être testé. Sans test, c'est du code mort qui ne marchera pas le jour où on en a besoin.

## Actions
```bash
# Chercher l'invocation dans la pipeline parent ou child
grep -rE "alembic (downgrade|upgrade).*alembic (upgrade|downgrade)" \
  .gitlab-ci.yml ci/ \
  || echo "FAIL: pipeline ne teste pas le cycle downgrade/upgrade"

# Alternative : dans le run_tests.sh du Backend
for d in apis/internal/*/run_tests.sh; do
  grep -qE "downgrade -1" "$d" \
    || echo "WARN: $d ne teste pas le downgrade"
done
```

## Implémentation typique
```bash
# apis/internal/<svc>-backend-api/run_tests.sh
alembic upgrade head
alembic downgrade -1
alembic upgrade head
pytest tests/
```
