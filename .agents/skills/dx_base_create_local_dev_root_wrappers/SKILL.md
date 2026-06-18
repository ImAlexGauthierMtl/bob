---
name: dx_base_create_local_dev_root_wrappers
description: Génère les wrappers run.sh, test.sh, lint.sh à la racine du projet.
metadata:
  reference: § 11
---

# dx_base_create_local_dev_root_wrappers

## Sortie
- run.sh : compose up -d + wait healthchecks + migrate par API + smoke local
- test.sh : itère sur les APIs et frontend, exécute leurs run_tests.sh
- lint.sh : ruff check + mypy + npm run lint
