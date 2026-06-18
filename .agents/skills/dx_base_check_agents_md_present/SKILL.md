---
name: dx_base_check_agents_md_present
description: Vérifie qu'AGENTS.md existe à la racine du projet, mentionne la source de vérité de l'architecture et la version des skills.
metadata:
  reference: § 10.3 + § 10.4
---

# dx_base_check_agents_md_present

## Actions
```bash
[ -f AGENTS.md ] || { echo "FAIL: AGENTS.md absent"; exit 1; }

# Doit pointer vers la doc d'architecture
grep -qE "regles-architecture-deploiement|docs/architecture" AGENTS.md \
    || echo "FAIL: AGENTS.md ne référence pas la doc d'architecture"

# Doit mentionner update-skills.sh ou .skills-version
grep -qE "(update-skills\.sh|\.skills-version)" AGENTS.md \
    || echo "WARN: AGENTS.md ne mentionne pas update-skills.sh"
```
