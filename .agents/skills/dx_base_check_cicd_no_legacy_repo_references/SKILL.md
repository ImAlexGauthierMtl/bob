---
name: dx_base_check_cicd_no_legacy_repo_references
description: Vérifie qu'aucun fichier du projet ne référence les anciens noms : infrastructure/ci-templates, shared/cicd-templates, shared/ci-template, gitlab.example.com.
metadata:
  reference: § 4.1
---

# dx_base_check_cicd_no_legacy_repo_references

## Actions
```bash
for pat in "infrastructure/ci-templates" "shared/cicd-templates" "shared/ci-template" "gitlab\.example\.com"; do
    hits=$(grep -rnE "$pat" --include="*.yml" --include="*.yaml" --include="*.sh" \
            --include="*.md" --include="*.py" \
            .gitlab-ci.yml deploy/ apis/ frontend/ docs/ 2>/dev/null | head -5)
    if [ -n "$hits" ]; then
        echo "FAIL: référence à '$pat' :"
        echo "$hits"
    fi
done
```
