---
name: dx_base_create_conventions_agents_md_v14
description: Génère un AGENTS.md à la racine du projet : source de vérité doc, conventions skills, refus absolus, comportement en cas de doute. Compatible v1.4 (agents-agnostique).
metadata:
  reference: § 10.3 + § 10.4
---

# dx_base_create_conventions_agents_md_v14

## Sections obligatoires
1. Source de vérité (`docs/architecture/regles-architecture-deploiement.md`)
2. Localisation des skills (`.agents/skills/dx_*/SKILL.md`)
3. Version trackée (`.agents/.skills-version`) + bump (`./.agents/update-skills.sh`)
4. Conventions skills (préfixe `dx_`, niveaux, verbes)
5. Tableau "Demande → Skill à invoquer"
6. Refus absolus (10 minimum : authentication, :latest, allow_failure, secrets, etc.)
7. Comportement en cas de doute

## Refus
- Refuser de mentionner un outil propriétaire spécifique (Cursor, Claude Code, Aider, Windsurf, Copilot, Kilo Code...)
- Refuser de créer un fichier `CLAUDE.md`, `.kilorules` etc. à la place de `AGENTS.md`
