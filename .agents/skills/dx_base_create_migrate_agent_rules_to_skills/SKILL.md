---
name: dx_base_create_migrate_agent_rules_to_skills
description: Migre les règles présentes dans des fichiers d'outils tiers (.cursorrules, .windsurfrules, CLAUDE.md...) : extrait les règles utiles, les porte dans des skills dx_* (PR repo central) ou AGENTS.md, puis supprime les fichiers d'outils.
metadata:
  reference: § 10.3
---

# dx_base_create_migrate_agent_rules_to_skills

## Actions
1. Inventorier les fichiers de règles d'outils présents (cf. `dx_base_check_agent_rules_single_source`)
2. Pour chaque règle utile trouvée : vérifier si un `dx_*` la couvre déjà
   - si oui → rien à porter
   - si non → ouvrir une PR sur `croo-dev/code-agent-skills-v1.0` (nouveau skill ou enrichissement), ou ajouter au `AGENTS.md` du projet si purement local
3. Supprimer les fichiers d'outils via `cleanup-tool-dirs.sh`
4. Vérifier : plus aucun fichier de règles tiers, `.agents/skills/` + `AGENTS.md` présents

## Refus
- Refuser de recopier des règles d'outil dans le projet sans les porter en skill
- Refuser de conserver un `.cursorrules`/`CLAUDE.md` "au cas où"
