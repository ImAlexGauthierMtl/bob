---
name: dx_base_check_agent_rules_single_source
description: Vérifie que les règles suivies par les agents proviennent uniquement de .agents/skills + AGENTS.md, et qu'aucun fichier de règles d'outil tiers ne subsiste (.cursorrules, .windsurfrules, .kilorules, CLAUDE.md, .github/copilot-instructions.md, .kilocode/).
metadata:
  reference: § 10.3
---

# dx_base_check_agent_rules_single_source

## Règle
Source de vérité unique : le repo `croo-dev/code-agent-skills-v1.0`, matérialisé dans le projet par `.agents/skills/` + `AGENTS.md`. Tout fichier de règles d'outil tiers est supprimé et remplacé.

## Actions
```bash
# Fichiers de règles d'outils tiers — doivent être ABSENTS
RULE_FILES=".cursorrules .windsurfrules .kilorules .clinerules CLAUDE.md .github/copilot-instructions.md"
for f in $RULE_FILES; do
    [ -e "$f" ] && echo "FAIL: fichier de règles d'outil tiers présent : $f (porter la règle dans un skill)"
done

# Dossiers de règles d'outils
for d in .kilocode .cursor .continue .windsurf; do
    [ -d "$d" ] && echo "FAIL: dossier de règles d'outil présent : $d/"
done

# Source unique présente
[ -d .agents/skills ] || echo "FAIL: .agents/skills/ absent (source de règles)"
[ -f AGENTS.md ]      || echo "FAIL: AGENTS.md absent"
```

## Remédiation
`cleanup-tool-dirs.sh` purge, `install.sh` pose les skills. Toute règle à conserver
est portée dans un `dx_*` via PR sur le repo central — jamais réintroduite localement.
