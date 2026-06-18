---
name: dx_base_check_conventions_no_dead_code
description: Détecte du code mort manifeste : fonctions définies non importées, imports inutilisés, fichiers orphelins.
metadata:
  reference: § 10
---

# dx_base_check_conventions_no_dead_code

## Actions
```bash
cd apis/internal/*/  # pour chaque
ruff check --select F401,F841 .  # imports / variables inutilisés
vulture src/ --min-confidence 80 || true
```
