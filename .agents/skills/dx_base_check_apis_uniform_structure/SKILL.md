---
name: dx_base_check_apis_uniform_structure
description: Vérifie que TOUTES les APIs (B4F et Backend) ont exactement la même structure de couches et les mêmes noms de fichiers : domain/application/infrastructure/presentation, routes.py, schemas.py, deps.py, main.py, config.py. Toute dérive est une violation.
metadata:
  reference: § 12.1
---

# dx_base_check_apis_uniform_structure

## Règle
Uniformité **stricte** : un agent doit pouvoir prédire l'emplacement de chaque fichier dans n'importe quelle API.

## Actions
```bash
REQUIRED_DIRS="domain application infrastructure presentation"
REQUIRED_FILES="presentation/main.py infrastructure/config.py"

fail=0
for api in apis/exposed/*/ apis/internal/*/; do
    [ -d "$api/src" ] || continue
    name=$(basename "$api")
    pkg=$(find "$api/src" -maxdepth 1 -mindepth 1 -type d | head -1)
    [ -n "$pkg" ] || { echo "FAIL: $name sans package src/"; fail=1; continue; }
    for d in $REQUIRED_DIRS; do
        [ -d "$pkg/$d" ] || { echo "FAIL: $name manque la couche $d/"; fail=1; }
    done
    for f in $REQUIRED_FILES; do
        [ -f "$pkg/$f" ] || { echo "FAIL: $name manque $f"; fail=1; }
    done
done
[ "$fail" -eq 0 ] && echo "OK: structure uniforme"
```

## Comparaison croisée
Pour deux APIs A et B, l'ensemble des chemins relatifs sous `src/<pkg>/` (dossiers)
doit être identique. Lister et diff :
```bash
list_layers() { (cd "$1/src"/*/ && find . -type d | sort); }
diff <(list_layers apis/internal/rooms-backend-api) \
     <(list_layers apis/internal/clients-backend-api) \
     && echo "OK uniformes" || echo "FAIL: structures divergentes"
```
