---
name: dx_base_create_api_b4f_scaffold
description: Crée le squelette d'une nouvelle B4F API sous apis/exposed/<name>-b4f-api/ : Dockerfile, pyproject, src/<name>_b4f_api/ avec les 4 couches Clean Archi, run_api.sh, run_tests.sh.
metadata:
  reference: § 2.1 + § 12
---

# dx_base_create_api_b4f_scaffold

## Refus
- Si le nom contient `authentication` → refuser
- Si pas de suffixe `-b4f-api` → refuser

## Actions
Créer l'arborescence + Dockerfile FastAPI + pyproject.toml + fichiers minimum (`main.py`, `routes.py`, `schemas.py`, `deps.py`, `config.py`).
Ajouter Redis client en `infrastructure/messaging/` si la B4F doit consommer des events.
