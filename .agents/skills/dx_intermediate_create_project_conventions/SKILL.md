---
name: dx_intermediate_create_project_conventions
description: Pose les conventions transverses d'un nouveau projet — squelette de /docs, /data, README avec badges, AGENTS.md, nettoyage de tous les outillages IA spécifiques, création des trois niveaux de shared/ (apis/shared, apis/exposed/shared, apis/internal/shared) vides. À invoquer au tout début d'un bootstrap projet, avant la création des APIs et du frontend.
metadata:
  reference: § 10 + § 11 (intersection scripts racine) de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_project_conventions

## Paramètres

- Nom du projet (slug)
- URL du repo central (par défaut `git@gitlab.tools.thesmartcrew.com:croo-dev/ci-cd-unified-template-v1.0.git`)
- Version du repo central à pinner (par défaut `v1`)

## Workflow

### 1. Arborescence racine

```
<projet>/
├── README.md                  # avec badges pipeline + coverage
├── AGENTS.md                  # instructions agent projet
├── CHANGELOG.md
├── LICENSE
├── .gitlab-ci.yml             # uniquement include du repo central
├── .gitignore                 # exclut .env, dist, node_modules, __pycache__
├── .env.example               # template (sans secrets prod)
├── apis/
│   ├── shared/
│   ├── exposed/
│   │   └── shared/
│   └── internal/
│       └── shared/
├── frontend/                  # créé par dx_intermediate_create_frontend_ngrx
├── deploy/
│   └── values/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── docs/                      # § 10.1
├── data/                      # § 10.2
└── docker-compose.yml         # créé par dx_intermediate_create_local_dev
```

### 2. Nettoyage outillages IA

```bash
rm -rf .cursor .cursorrules .cursorignore \
       .aider* .aiderconfig \
       .continue .continuerc \
       .windsurf .windsurfrules \
       .codeium* \
       .github/copilot-instructions.md
```

Conserver : `.agents/` + `AGENTS.md` (agents-agnostique), outils standards (`.editorconfig`, `.prettierrc`, `pyproject.toml`...)
(`.editorconfig`, `.prettierrc`, `pyproject.toml`).

### 3. `.gitlab-ci.yml`

```yaml
include:
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1
    file: '/templates/parent.yml'
```

### 4. README avec badges

```markdown
# <projet>

![pipeline](https://gitlab.tools.thesmartcrew.com/<group>/<projet>/badges/main/pipeline.svg)
![coverage](https://gitlab.tools.thesmartcrew.com/<group>/<projet>/badges/main/coverage.svg)
```

### 5. AGENTS.md projet

Fichier minimal qui pointe vers ce repo de skills et précise que le projet
suit les règles de `docs/architecture/regles-architecture-deploiement.md` (la
doc peut être un lien symbolique vers le repo de skills, ou une copie locale).

## Base skills

- `dx_base_create_project_root_skeleton`
- `dx_base_create_install_skills_in_project` — copie versionnée des skills (v1.4)
- `dx_base_create_cleanup_tool_dirs` — supprime `.kilo*`, `.cursor*`, etc. (v1.4)
- `dx_base_create_conventions_agents_md_v14` — AGENTS.md sans mention d'outil propriétaire
- `dx_base_create_update_skills_workflow` — bootstrap du workflow de bump
- `dx_base_create_migrate_agent_rules_to_skills` — porte les règles d'outils tiers en skills puis purge (v1.6)
- `dx_base_create_shared_auth_rbac_audit` — primitives transverses dans apis/shared (v1.6)
- `dx_base_create_shared_python_packaging` — shared en modules Python éditables (v1.6)

## Anti-patterns

1. Créer `apis/`, `frontend/` etc. sans d'abord nettoyer les outillages IA
   (les fichiers parasites resteront)
2. Mettre la doc dans `README.md` géant — toujours `/docs`
3. Commiter `.env` (le rajouter dans `.gitignore`)
4. Démarrer sans tester que `include:` du `.gitlab-ci.yml` résout (le repo
   central doit exister et publier la ref pointée)
5. **Mentionner un outil IA propriétaire** dans `AGENTS.md` ou `README.md` (Cursor, Claude Code, Aider, Windsurf, Copilot, Kilo Code...) — viole § 10.3
6. **Symlinker `.agents/skills/`** au lieu de copier — viole § 10.4
7. **Créer `.kilocode/modes/`** ou tout autre dossier d'outil — viole § 10.3
8. **Oublier `.agents/.skills-version`** — la version installée doit être trackée
