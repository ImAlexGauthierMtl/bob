---
name: dx_base_create_update_skills_workflow
description: Configure le workflow de bump des skills : update-skills.sh dans .agents/, AGENTS.md qui mentionne le bump, optionnel .gitlab-ci.yml job 'skills-bump' pour notifier sur nouvelle version.
metadata:
  reference: § 10.4
---

# dx_base_create_update_skills_workflow

## Actions
1. Vérifier que `.agents/update-skills.sh` est présent (sinon le copier depuis le repo central)
2. Vérifier que AGENTS.md mentionne la commande de bump
3. (Optionnel) Ajouter un job CI dans `.gitlab-ci.yml` qui vérifie `dx_base_check_skills_version_tracked` et compare à la dernière version du repo central, signale en MR si décalé

## Cron de bump (optionnel)
Configurer un job CI mensuel qui exécute :
```bash
./.agents/update-skills.sh
```
et ouvre automatiquement une MR si un bump est disponible.
