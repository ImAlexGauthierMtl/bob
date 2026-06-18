---
name: dx_base_create_cleanup_tool_dirs
description: Supprime tous les dossiers/fichiers d'outils IA spécifiques d'un projet : .kilo*, .cursor*, .claude*, .aider*, .continue*, .windsurf*, .codeium*, .copilot*, CLAUDE.md, .github/copilot-instructions.md.
metadata:
  reference: § 10.3
---

# dx_base_create_cleanup_tool_dirs

## Actions
```bash
find . -maxdepth 3 \
    \( -name '.kilo*' -o -name '.cursor*' -o -name '.claude*' \
       -o -name '.aider*' -o -name '.continue*' -o -name '.windsurf*' \
       -o -name '.codeium*' -o -name '.copilot*' -o -name 'CLAUDE.md' \) \
    -not -path './.git/*' -not -path './node_modules/*' \
    -exec rm -rf {} +
rm -f .github/copilot-instructions.md
```
Puis :
```bash
git add -A
git commit -m "chore: remove tool-specific AI config (§ 10.3)"
```
