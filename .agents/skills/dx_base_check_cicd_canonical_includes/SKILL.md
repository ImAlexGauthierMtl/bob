---
name: dx_base_check_cicd_canonical_includes
description: Vérifie que le .gitlab-ci.yml du projet contient exactement 2 file-includes, tous deux du repo croo-dev/ci-cd-unified-template-v1.0 (/kaniko.yml + /templates/parent.yml), avec la même ref taguée. Aucune référence à infrastructure/ci-templates ou shared/cicd-templates.
metadata:
  reference: § 4.1
---

# dx_base_check_cicd_canonical_includes

## Format canonique (v1.4 doc)
```yaml
include:
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1.0.64
    file: '/kaniko.yml'
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1.0.64
    file: '/templates/parent.yml'
```

## Actions
```bash
f=".gitlab-ci.yml"
[ -f "$f" ] || { echo "FAIL: $f absent"; exit 1; }

# 1. Les deux project: pointent sur croo-dev/ci-cd-unified-template-v1.0
n_total=$(grep -cE "^\s*-\s*project:" "$f")
n_ok=$(grep -cE "project:\s*['\"]?croo-dev/ci-cd-unified-template-v1\.0['\"]?" "$f")
[ "$n_total" = "$n_ok" ] || echo "FAIL: include(s) vers un autre repo ($((n_total-n_ok)))"

# 2. Les deux files attendus
grep -qE "file:\s*['\"]?/kaniko\.yml['\"]?" "$f"            || echo "FAIL: /kaniko.yml manquant"
grep -qE "file:\s*['\"]?/templates/parent\.yml['\"]?" "$f"  || echo "FAIL: /templates/parent.yml manquant"

# 3. Refs identiques + jamais main
refs=$(grep -E "^\s*ref:" "$f" | awk '{print $2}' | tr -d "'\"" | sort -u)
[ "$(echo "$refs" | wc -l)" = "1" ] || echo "FAIL: refs différentes entre les 2 includes: $refs"
echo "$refs" | grep -qE "^(main|master)$" && echo "FAIL: ref main/master interdit"

# 4. Anciens repos morts
for old in "infrastructure/ci-templates" "shared/cicd-templates" "shared/ci-template"; do
    grep -q "$old" "$f" && echo "FAIL: référence à '$old'"
done
```
