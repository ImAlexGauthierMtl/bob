---
name: dx_base_check_conventions_no_ai_garbage
description: Vérifie l'absence de garbage IA (fichiers .bak, .copy, *_v2.py, prompt-history.md, anciennes brouillons commit).
metadata:
  reference: § 10
---

# dx_base_check_conventions_no_ai_garbage

## Actions
```bash
find . -name "*.bak" -o -name "*.copy" -o -name "*_v[0-9].*" -o -name "*-old.*" -o -name "*draft*"       | grep -v node_modules | grep -v .git
```
