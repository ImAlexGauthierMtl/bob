---
name: dx_base_create_shared_python_packaging
description: Configure le packaging Python du monorepo pour importer apis/shared, apis/exposed/shared, apis/internal/shared comme modules locaux éditables (pas de vendoring, pas de symlink, pas de publication).
metadata:
  reference: § 2.10
---

# dx_base_create_shared_python_packaging

## Actions
Dans chaque `pyproject.toml` d'API, déclarer les shared comme sources locales :
```toml
[tool.uv.sources]
app-shared          = { path = "../../shared", editable = true }
app-internal-shared = { path = "../shared",    editable = true }   # Backend
# ou app-exposed-shared pour les B4F
```
Le contexte Docker = racine du repo (cf. § 4.10) pour que les `COPY` voient les shared.

## Refus
- Refuser de générer un symlink vers un shared
- Refuser de copier un shared dans l'API (vendoring)
- Refuser d'ajouter `[project] version=` à un shared (le rendrait publiable)
