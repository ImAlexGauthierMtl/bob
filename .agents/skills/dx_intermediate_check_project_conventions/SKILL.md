---
name: dx_intermediate_check_project_conventions
description: Verdict pass/fail des conventions projet selon § 10 et § 8.7. Vérifie /docs centralisée, /data pour les données client (aucune non anonymisée commitée), aucun fichier de config d'outil IA spécifique (config agents-agnostique : .agents/ + AGENTS.md), code partagé organisé en apis/shared, apis/exposed/shared, apis/internal/shared sans logique métier.
metadata:
  reference: § 10 + § 8.7 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_project_conventions

## Périmètre — § 8.7

```
- [ ] /docs à la racine pour toute la doc
- [ ] /data à la racine pour les données client
- [ ] Aucun document libre dans apis/, frontend/, deploy/
- [ ] Aucune donnée client réelle non anonymisée commitée
- [ ] Aucun fichier de config d'outil IA spécifique (ni .kilo*, ni .cursor*, ni .claude*, etc.)
- [ ] Trois niveaux de code partagé : apis/shared/, apis/exposed/shared/, apis/internal/shared/
- [ ] Aucune logique métier dans les shared/
- [ ] Aucun modèle d'entité partagé entre Backends
- [ ] apis/exposed/shared/ ne consomme pas apis/internal/shared/
```

## Base skills

- `dx_base_check_convention_docs_in_docs`
- `dx_base_check_convention_data_in_data`

### Code partagé (v1.6 — strict)

- `dx_base_check_shared_three_layers` — apis/shared, exposed/shared, internal/shared + sens de dépendance
- `dx_base_check_shared_auth_rbac_centralized` — auth + RBAC dans apis/shared, jamais réimplémentés
- `dx_base_check_shared_audit_logs_centralized` — audit + logger JSON uniques dans apis/shared
- `dx_base_check_shared_no_business_logic` — aucune logique/entité métier dans shared/
- `dx_base_check_shared_imported_as_python_module` — modules Python, pas de vendoring ni de lib publiée
- `dx_base_check_no_symlinks_in_apis` — aucun symlink sous apis/

### Source de règles agents unique (v1.6)

- `dx_base_check_agent_rules_single_source` — règles issues uniquement de .agents/skills + AGENTS.md

### Agents-agnostique (v1.4)

- `dx_base_check_no_tool_specific_dirs` — aucun `.kilo*`, `.cursor*`, `.claude*`, `.aider*`, etc.
- `dx_base_check_agents_dir_present` — `.agents/skills/` présent, contient des `dx_*`, est commité
- `dx_base_check_agents_md_present` — `AGENTS.md` à la racine, référence la doc d'architecture
- `dx_base_check_skills_version_tracked` — `.agents/.skills-version` au format `vX[.Y[.Z]]`
- `dx_base_check_update_skills_script_present` — `.agents/update-skills.sh` exécutable, pointe sur le bon repo
- `dx_base_check_no_symlinks_in_agents` — pas de symlinks (copie versionnée, § 10.4)
- `dx_base_check_skills_not_modified_locally` — les SKILL.md ne sont modifiés que via bump

Les checks v1.0 orientés outil unique ont été **supprimés** en v1.5 au profit du modèle agents-agnostique.

Format § 9.
