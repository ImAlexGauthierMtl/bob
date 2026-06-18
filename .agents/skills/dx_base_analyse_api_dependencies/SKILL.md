---
name: dx_base_analyse_api_dependencies
description: Cartographie les dépendances inter-APIs : qui appelle qui (HTTP) et qui publie/souscrit (Redis events). À invoquer pour produire un graphe avant refactor.
metadata:
  reference: § 2.3
---

# dx_base_analyse_api_dependencies

## Actions
```bash
grep -rE "httpx|requests" apis/internal/*/src/ apis/exposed/*/src/ | grep -oE "[a-z-]+-(b4f|backend)-api"
grep -rE "publish|subscribe" apis/internal/*/src/ | grep -oE "channel.*[a-z_.]+"
```
Sortir un tableau "depuis → vers" avec type (HTTP / event).
