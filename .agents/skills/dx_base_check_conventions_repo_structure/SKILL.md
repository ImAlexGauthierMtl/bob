---
name: dx_base_check_conventions_repo_structure
description: Vérifie l'arborescence racine attendue : apis/, frontend/, deploy/, docs/, .gitlab-ci.yml, AGENTS.md, README.md, CHANGELOG.md.
metadata:
  reference: § 10 + § 8.7
---

# dx_base_check_conventions_repo_structure

## Actions
```bash
for f in apis frontend deploy docs .gitlab-ci.yml AGENTS.md README.md CHANGELOG.md; do
  [ -e "$f" ] || echo "FAIL: $f manquant"
done
```
