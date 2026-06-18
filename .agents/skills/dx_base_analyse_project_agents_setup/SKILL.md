---
name: dx_base_analyse_project_agents_setup
description: Cartographie la configuration agents-agnostique du projet : présence et version des skills, AGENTS.md, dossiers interdits restants.
metadata:
  reference: § 10.3 + § 10.4
---

# dx_base_analyse_project_agents_setup

## Actions
```bash
echo "=== .agents/skills/ ==="
ls .agents/skills/ 2>/dev/null | head -20
echo ""
echo "=== Version installée ==="
cat .agents/.skills-version 2>/dev/null || echo "(absent)"
echo ""
echo "=== AGENTS.md (premières lignes) ==="
head -10 AGENTS.md 2>/dev/null || echo "(absent)"
echo ""
echo "=== Dossiers/fichiers d'outils IA (§ 10.3 interdit) ==="
find . -maxdepth 3 \
    \( -name '.kilo*' -o -name '.cursor*' -o -name '.claude*' \
       -o -name '.aider*' -o -name '.continue*' -o -name '.windsurf*' \
       -o -name '.codeium*' -o -name '.copilot*' -o -name 'CLAUDE.md' \) \
    -not -path './.git/*' 2>/dev/null
```
