---
name: dx_base_check_shared_imported_as_python_module
description: Vérifie que les shared/ sont consommés comme modules Python du monorepo (sources locales éditables dans pyproject.toml), jamais vendorés (copie dans une API), jamais packagés en bibliothèque externe publiée.
metadata:
  reference: § 2.10 + § 12.5
---

# dx_base_check_shared_imported_as_python_module

## Actions
```bash
# 1. Aucune copie/vendoring d'un shared dans une API
find apis/exposed apis/internal -type d \( -name vendor -o -name _shared -o -name _vendor \) 2>/dev/null \
    | grep . && echo "FAIL: dossier de vendoring détecté"

# 2. Les pyproject.toml référencent les shared par chemin local éditable
for pp in apis/exposed/*/pyproject.toml apis/internal/*/pyproject.toml; do
    [ -f "$pp" ] || continue
    grep -qE "(path *=|editable *= *true|tool\.uv\.sources|\.\./shared|\.\./\.\./shared)" "$pp" \
        || echo "WARN: $pp ne déclare pas les shared comme sources locales éditables"
done

# 3. Aucun shared publié comme paquet externe (pas d'index, pas de build wheel dédié)
for d in apis/shared apis/exposed/shared apis/internal/shared; do
    [ -f "$d/pyproject.toml" ] && grep -qE "\[project\]" "$d/pyproject.toml" \
        && grep -qE "version *=" "$d/pyproject.toml" \
        && echo "WARN: $d ressemble à un paquet publiable — il doit rester module interne"
done
```
