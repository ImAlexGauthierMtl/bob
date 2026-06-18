---
name: dx_base_check_no_symlinks_in_apis
description: Vérifie qu'aucun symlink n'existe sous apis/ : les couches et les shared/ sont référencés par import Python uniquement, jamais par lien symbolique.
metadata:
  reference: § 2.10 + § 12.3
---

# dx_base_check_no_symlinks_in_apis

## Actions
```bash
links=$(find apis/ -type l 2>/dev/null)
[ -z "$links" ] || {
    echo "FAIL: symlinks interdits sous apis/ :"
    echo "$links" | sed 's|^|  |'
    exit 1
}
```
Idem pour `.agents/skills/` (cf. `dx_base_check_no_symlinks_in_agents`).
