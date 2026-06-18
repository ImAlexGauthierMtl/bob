---
name: dx_base_create_alembic_run_tests_with_downgrade
description: Génère / modifie run_tests.sh d'un Backend pour tester le cycle upgrade → downgrade → upgrade avant les pytest.
metadata:
  reference: § 2.7.5
---

# dx_base_create_alembic_run_tests_with_downgrade

## Sortie
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[test] alembic upgrade head"
alembic upgrade head

echo "[test] alembic downgrade -1 (vérifie la réversibilité)"
alembic downgrade -1

echo "[test] alembic upgrade head (réapplique)"
alembic upgrade head

echo "[test] pytest"
pytest --cov --cov-report=xml --junitxml=junit.xml
```
Le double cycle prouve : (a) le downgrade tourne sans erreur, (b) l'upgrade est ré-applicable après un downgrade.
