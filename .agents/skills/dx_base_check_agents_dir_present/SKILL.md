---
name: dx_base_check_agents_dir_present
description: Vérifie que .agents/skills/ existe dans le projet, contient des dx_* et est commité (pas dans .gitignore).
metadata:
  reference: § 10.4 + § 8.7
---

# dx_base_check_agents_dir_present

## Actions
```bash
[ -d .agents/skills ] || { echo "FAIL: .agents/skills/ absent"; exit 1; }

n=$(find .agents/skills -maxdepth 1 -type d -name "dx_*" | wc -l)
[ "$n" -gt 0 ] || echo "FAIL: aucun skill dx_* dans .agents/skills/"

# .agents/ ne doit PAS être dans .gitignore
if [ -f .gitignore ] && grep -qE '^\.?agents/?$|^\.agents/skills/?$' .gitignore; then
    echo "FAIL: .agents/ ou .agents/skills/ dans .gitignore (viole § 10.4)"
fi

# Doit être tracké par git
if [ -d .git ] && ! git ls-files .agents/ | head -1 | grep -q .; then
    echo "FAIL: .agents/ non commité (viole § 10.4 — autonomie du projet)"
fi
```
