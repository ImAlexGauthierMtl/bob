---
name: dx_base_check_conventions_agents_md_present
description: Vérifie qu'un AGENTS.md à la racine décrit les conventions pour les agents, quel que soit l'outil.
metadata:
  reference: § 10
---

# dx_base_check_conventions_agents_md_present

## Actions
```bash
[ -f AGENTS.md ] || echo "FAIL: AGENTS.md absent"
```
Contenu minimum : pointeur vers docs/architecture/regles-architecture-deploiement.md, conventions de nommage, localisation des skills (.agents/skills/), refus absolus.
