---
name: dx_intermediate_analyse_project_conventions
description: Analyse les conventions transverses du projet selon le chapitre 10 — emplacement de la doc (/docs), des données client (/data), configuration agents-agnostique (.agents/skills/ + AGENTS.md, aucun dossier d'outil spécifique : .kilo, .cursor, .claude, .aider, .continue, .windsurf, .codeium, copilot-instructions). Inventaire des fichiers de config IA traînants et des données client non anonymisées commitées.
metadata:
  reference: § 10 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_project_conventions

## Périmètre

- `/docs` à la racine, sous-arborescence libre, doc projet centralisée (§ 10.1)
- `/data` à la racine pour échantillons, fixtures, exports (§ 10.2)
- Outillage IA : **agents-agnostique** — `.agents/` + `AGENTS.md` uniquement (§ 10.3) ; skills copiés/versionnés (§ 10.4)

## Détection

```bash
# Fichiers d'autres outils IA
find . -maxdepth 4 -type f \( \
  -name '.cursorrules' -o -name '.cursorignore' \
  -o -name '.aiderconfig' -o -name '.aider*' \
  -o -name '.continuerc' -o -name '.windsurfrules' \
  -o -name '.codeium*' \
\)

# Répertoires d'autres outils IA
find . -maxdepth 3 -type d \( \
  -name '.cursor' -o -name '.continue' -o -name '.aider' \
  -o -name '.windsurf' -o -name '.codeium' \
\)

# copilot-instructions
find . -path '*.github/copilot-instructions.md'

# Documents éparpillés hors /docs
find . -name '*.md' -not -path './docs/*' -not -path './node_modules/*' \
  -not -name 'README.md' -not -name 'CONTRIBUTING.md' \
  -not -name 'CHANGELOG.md' -not -name 'LICENSE' -not -name 'AGENTS.md'

# Données dans des dossiers non /data
find . -name '*.csv' -o -name '*.json' -not -path './node_modules/*' \
  | grep -v '^./data/' | grep -v 'package'
```

## Base skills

- `dx_base_check_convention_docs_in_docs`
- `dx_base_check_convention_data_in_data`
- `dx_base_check_convention_no_other_ai_tools`
- `dx_base_check_no_tool_specific_dirs`
- `dx_base_analyse_project_agents_setup`

## Format de sortie

```markdown
## Analyse Conventions projet (§ 10)

### Documentation
- Présence de /docs : oui / non
- Documents libres hors /docs : <liste>

### Données
- Présence de /data : oui / non
- Datasets potentiellement client hors /data : <liste>

### Outillage IA
- Fichiers d'outils IA spécifiques détectés : <liste>
- Action proposée : `rm -rf <liste>` puis commit
```
