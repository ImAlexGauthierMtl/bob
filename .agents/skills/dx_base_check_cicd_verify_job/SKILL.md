---
name: dx_base_check_cicd_verify_job
description: Vérifie que le stage build contient un job verify:<api> avec needs [build:<api>] qui interroge l'API Harbor (scan natif + signature Cosign). Aucun scan Trivy local dans le pipeline.
metadata:
  reference: § 4.10
---

# dx_base_check_cicd_verify_job

## Règle (v1.4 doc)
Le scan vit côté Harbor (auto-scan on push + auto-sign Cosign). Le pipeline fait un `verify:<api>` qui poll l'API Harbor.

## Actions
```bash
# 1. verify généré par discover-apis.sh (audit repo CI/CD) ou présent dans le child
grep -rE "verify:" templates/child/stages/build.yml deploy/scripts/discover-apis.sh 2>/dev/null \
    | grep -q . || echo "FAIL: pas de job verify"

# 2. verify a needs: [build:<api>]
grep -A10 "\.verify_template" templates/child/stages/build.yml 2>/dev/null | grep -q "needs" \
    || echo "WARN: vérifier le needs du verify"

# 3. AUCUN scan Trivy local
grep -rE "aquasec/trivy|trivy image" \
    --include="*.yml" --include="*.yaml" --include="*.sh" \
    . 2>/dev/null | grep -v harbor-cve-whitelist \
    | grep . && echo "FAIL: scan Trivy local interdit (le scan vit côté Harbor)"

# 4. Image verify pinnée
grep -qE "harbor-verify:v[0-9]" templates/child/stages/build.yml 2>/dev/null \
    || echo "WARN: image harbor-verify non pinnée"
```
