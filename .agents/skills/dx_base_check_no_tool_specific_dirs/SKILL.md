---
name: dx_base_check_no_tool_specific_dirs
description: Vérifie qu'AUCUN dossier ou fichier d'outil IA spécifique n'existe : .kilo, .kilocode, .cursor, .claude, .aider, .continue, .windsurf, .codeium, .copilot, CLAUDE.md, .github/copilot-instructions.md.
metadata:
  reference: § 10.3 + § 8.7
---

# dx_base_check_no_tool_specific_dirs

## Règle
Le projet est **agents-agnostique**. Toute configuration IA passe par `.agents/` et `AGENTS.md`. Tout fichier nommé d'après un outil spécifique est interdit.

## Actions
```bash
forbidden=$(find . -maxdepth 3 \
    \( -name '.kilo*' -o -name '.cursor*' -o -name '.claude*' \
       -o -name '.aider*' -o -name '.continue*' -o -name '.windsurf*' \
       -o -name '.codeium*' -o -name '.copilot*' -o -name 'CLAUDE.md' \) \
    -not -path './.git/*' -not -path './node_modules/*' \
    2>/dev/null)

[ -z "$forbidden" ] || {
    echo "FAIL: dossiers/fichiers d'outils IA interdits :"
    echo "$forbidden" | sed 's|^|  |'
    exit 1
}

# .github/copilot-instructions.md séparément
[ -f .github/copilot-instructions.md ] && echo "FAIL: .github/copilot-instructions.md interdit"
```

## Remédiation
Utiliser le script `cleanup-tool-dirs.sh` du repo central, qui supprime tous ces fichiers en une commande.
