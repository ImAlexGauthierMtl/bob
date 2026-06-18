---
name: dx_base_check_skills_not_modified_locally
description: Vérifie qu'aucun SKILL.md sous .agents/skills/ n'a été modifié localement (toute évolution passe par PR sur le repo central).
metadata:
  reference: § 10.4
---

# dx_base_check_skills_not_modified_locally

## Règle
Les SKILL.md sont la propriété du repo central. Modifier en local revient à diverger silencieusement.

## Actions
```bash
# Vérifier qu'aucun fichier de .agents/skills/ n'a un commit récent
# qui ne corresponde pas à un "chore(skills): bump to vX.Y.Z"
if [ -d .git ]; then
    recent=$(git log --pretty=format:'%H %s' -- .agents/skills/ 2>/dev/null | head -10)
    non_bump=$(echo "$recent" | grep -vE 'chore\(skills\): (bump|install)' || true)
    if [ -n "$non_bump" ]; then
        echo "WARN: commits manuels détectés sur .agents/skills/ :"
        echo "$non_bump" | sed 's|^|  |' | head -5
        echo "  Voir § 10.4 : toute évolution passe par PR sur croo-dev/code-agent-skills-v1.0"
    fi
fi
```
