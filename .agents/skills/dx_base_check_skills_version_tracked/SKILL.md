---
name: dx_base_check_skills_version_tracked
description: Vérifie que .agents/.skills-version existe et contient un tag valide (vX.Y.Z ou vX) — sinon impossible de savoir quelle version est installée.
metadata:
  reference: § 10.4
---

# dx_base_check_skills_version_tracked

## Actions
```bash
[ -f .agents/.skills-version ] || { echo "FAIL: .agents/.skills-version absent"; exit 1; }

v=$(cat .agents/.skills-version | tr -d '[:space:]')
echo "$v" | grep -qE "^v[0-9]+(\.[0-9]+){0,2}$|^v[0-9]+\.[0-9]+\.[0-9]+-[a-z0-9]+$" \
    || echo "FAIL: .skills-version contient '$v' (format attendu: vMAJOR[.MINOR[.PATCH]])"
```
