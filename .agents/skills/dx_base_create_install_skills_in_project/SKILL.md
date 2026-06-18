---
name: dx_base_create_install_skills_in_project
description: Installe une copie des skills `dx_*` dans un projet : .agents/skills/ + .agents/update-skills.sh + .agents/.skills-version + AGENTS.md (si absent).
metadata:
  reference: § 10.4
---

# dx_base_create_install_skills_in_project

## Actions
Reproduire ce que fait `scripts/install.sh` du repo central :
1. Audit § 10.3 (refus si dossiers d'outils IA présents, sauf FORCE=yes)
2. cp -r .agents/skills/dx_* (depuis le repo central) → .agents/skills/ du projet
3. cp scripts/update-skills.sh → .agents/update-skills.sh
4. echo "vX.Y.Z" > .agents/.skills-version
5. Générer AGENTS.md si absent

## Refus
- Refuser d'utiliser des symlinks (§ 10.4)
- Refuser de créer `.kilocode/`, `.cursor/` ou tout autre dossier d'outil spécifique
