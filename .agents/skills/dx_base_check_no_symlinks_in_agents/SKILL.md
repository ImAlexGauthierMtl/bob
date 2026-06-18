---
name: dx_base_check_no_symlinks_in_agents
description: Vérifie qu'aucun symlink ne traîne sous .agents/skills/ — la stratégie est copie versionnée, pas lien externe.
metadata:
  reference: § 10.4
---

# dx_base_check_no_symlinks_in_agents

## Actions
```bash
symlinks=$(find .agents/skills -type l 2>/dev/null)
[ -z "$symlinks" ] || {
    echo "FAIL: symlinks détectés sous .agents/skills/ :"
    echo "$symlinks" | sed 's|^|  |'
    echo "  v1.4+ : copie versionnée uniquement"
    exit 1
}
```
